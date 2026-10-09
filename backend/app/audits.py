import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from quart import Blueprint, current_app, g, jsonify
from sqlalchemy import select

from .discovery import PRIVATE_NETWORKS, normalize_url
from .models import Audit, AuditIssue, Lead, WorkspaceMember

bp = Blueprint("audits", __name__, url_prefix="/api")


@dataclass(frozen=True)
class PageFacts:
    url: str
    status_code: int
    html: str
    headers: dict[str, str]


@dataclass(frozen=True)
class RuleIssue:
    rule_id: str
    category: str
    severity: str
    explanation: str
    fix_recommendation: str
    evidence: dict
    confidence: int = 100


class AuditRule:
    rule_id = ""
    category = ""

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        raise NotImplementedError


class StatusRule(AuditRule):
    rule_id, category = "technical.status", "Technical"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        if page.status_code >= 400:
            return RuleIssue(self.rule_id, self.category, "CRITICAL", f"The page returned HTTP {page.status_code}.", "Restore the page and verify the server returns a successful response.", {"statusCode": page.status_code})
        return None


class HttpsRule(AuditRule):
    rule_id, category = "technical.https", "Technical"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        if urlparse(page.url).scheme != "https":
            return RuleIssue(self.rule_id, self.category, "HIGH", "The website is not using HTTPS.", "Install a valid TLS certificate and redirect HTTP traffic to HTTPS.", {})
        return None


class TitleRule(AuditRule):
    rule_id, category = "on_page.title", "On-page"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        match = re.search(r"<title[^>]*>(.*?)</title>", page.html, re.I | re.S)
        title = re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
        if not title:
            return RuleIssue(self.rule_id, self.category, "HIGH", "The homepage has no usable title tag.", "Add a concise title containing the business name and primary service.", {})
        return None


class MetaDescriptionRule(AuditRule):
    rule_id, category = "on_page.meta_description", "On-page"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        if not re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']+', page.html, re.I):
            return RuleIssue(self.rule_id, self.category, "MEDIUM", "The homepage has no meta description.", "Write a plain-language description that explains the local service and location.", {})
        return None


class HeadingRule(AuditRule):
    rule_id, category = "on_page.heading", "On-page"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        h1_count = len(re.findall(r"<h1(?:\s|>)", page.html, re.I))
        if h1_count != 1:
            return RuleIssue(self.rule_id, self.category, "MEDIUM", f"The homepage has {h1_count} H1 headings; it should have exactly one.", "Use one descriptive H1 for the main page purpose and use H2/H3 for sections.", {"h1Count": h1_count})
        return None


class ViewportRule(AuditRule):
    rule_id, category = "mobile.viewport", "Mobile"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        if not re.search(r'<meta[^>]+name=["\']viewport["\'][^>]+content=', page.html, re.I):
            return RuleIssue(self.rule_id, self.category, "HIGH", "The homepage is missing a mobile viewport declaration.", "Add a responsive viewport meta tag and test the page at phone widths.", {})
        return None


class ContactRule(AuditRule):
    rule_id, category = "conversion.contact", "Conversion"

    def evaluate(self, page: PageFacts) -> RuleIssue | None:
        if not re.search(r"(tel:|mailto:|whatsapp|contact)", page.html, re.I):
            return RuleIssue(self.rule_id, self.category, "MEDIUM", "No obvious contact or call-to-action signal was found.", "Place a visible phone, WhatsApp, email, or contact form action above the fold.", {})
        return None


RULES: tuple[AuditRule, ...] = (StatusRule(), HttpsRule(), TitleRule(), MetaDescriptionRule(), HeadingRule(), ViewportRule(), ContactRule())


async def _workspace_for_lead(lead_id):
    if not g.user:
        return None, None
    async with current_app.session_factory() as db:
        member = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == g.user.id))).scalars().first()
        if not member:
            return None, None
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == member.workspace_id))).scalar_one_or_none()
        return member.workspace_id, lead


async def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP(S) URLs can be audited.")
    loop = __import__("asyncio").get_running_loop()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    infos = await loop.run_in_executor(None, socket.getaddrinfo, parsed.hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    addresses = {info[4][0] for info in infos}
    if any(ipaddress.ip_address(address) in network for address in addresses for network in PRIVATE_NETWORKS):
        raise ValueError("Private or internal addresses are not allowed.")

async def _fetch_page(url: str) -> PageFacts:
    url = normalize_url(url) or ""
    async with httpx.AsyncClient(timeout=10, follow_redirects=False, headers={"User-Agent": "LeadPitchAudit/0.1"}) as client:
        for _ in range(5):
            await _validate_public_url(url)
            response = await client.get(url)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("The website returned an invalid redirect.")
                url = urljoin(url, location)
                continue
            if response.status_code >= 400:
                response.raise_for_status()
            return PageFacts(str(response.url), response.status_code, response.text[:1_000_000], dict(response.headers))
        raise ValueError("The website exceeded the redirect limit.")


def _score(issues: list[RuleIssue]) -> tuple[int, dict[str, int]]:
    categories = {rule.category for rule in RULES}
    penalties = {"CRITICAL": 30, "HIGH": 18, "MEDIUM": 10, "LOW": 4}
    scores = {category: 100 for category in categories}
    for issue in issues:
        scores[issue.category] = max(0, scores[issue.category] - penalties.get(issue.severity, 0))
    return round(sum(scores.values()) / len(scores)), scores


def _severity(score: int, status: str) -> tuple[str, list[str]]:
    if status in {"NO_WEBSITE", "DEAD_SITE"}:
        return "CRITICAL", ["No reachable website was available for audit."]
    if status == "SOCIAL_ONLY":
        return "HIGH", ["The listing points to a social profile rather than an owned website."]
    if score < 30:
        return "CRITICAL", [f"Overall audit score is {score}/100."]
    if score < 50:
        return "HIGH", [f"Overall audit score is {score}/100."]
    if score < 70:
        return "MEDIUM", [f"Overall audit score is {score}/100."]
    return "LOW", [f"Overall audit score is {score}/100."]


@bp.post("/leads/<uuid:lead_id>/audit")
async def run_audit(lead_id):
    workspace_id, lead = await _workspace_for_lead(lead_id)
    if not workspace_id:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    if not lead:
        return jsonify({"error": {"code": "not_found", "message": "Lead not found."}}), 404
    if not lead.website_url:
        return jsonify({"error": {"code": "validation_error", "message": "This lead does not have an auditable website."}}), 400
    page: PageFacts | None = None
    audit_url = normalize_url(lead.website_url) or ""
    try:
        page = await _fetch_page(audit_url)
        issues = [issue for rule in RULES if (issue := rule.evaluate(page))]
        overall, categories = _score(issues)
        status, reasons = _severity(overall, lead.website_status)
    except (httpx.HTTPError, OSError, ValueError) as error:
        overall, categories, issues = 0, {}, []
        status, reasons = "CRITICAL", [f"Audit could not reach the website: {error}"]
    async with current_app.session_factory() as db:
        audit = Audit(workspace_id=workspace_id, lead_id=lead.id, overall_score=overall, category_scores=categories)
        db.add(audit)
        await db.flush()
        affected_url = page.url if page else audit_url
        db.add_all([AuditIssue(audit_id=audit.id, rule_id=issue.rule_id, category=issue.category, severity=issue.severity, confidence=issue.confidence, affected_url=affected_url, explanation=issue.explanation, fix_recommendation=issue.fix_recommendation, evidence=issue.evidence) for issue in issues])
        lead.severity = status
        lead.opportunity_score = max(0, min(100, round((100 - overall) * 0.7 + (100 if status == "CRITICAL" else 70 if status == "HIGH" else 40) * 0.3)))
        lead.lead_value_tier = "HIGH" if lead.opportunity_score >= 70 else "MEDIUM" if lead.opportunity_score >= 40 else "LOW"
        await db.commit()
        return jsonify({"id": str(audit.id), "status": "COMPLETED", "overallScore": overall, "categoryScores": categories, "severity": status, "severityReasons": reasons, "issueCount": len(issues)}), 202


@bp.get("/audits/<uuid:audit_id>")
async def get_audit(audit_id):
    if not g.user:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    async with current_app.session_factory() as db:
        audit = (await db.execute(select(Audit).where(Audit.id == audit_id))).scalar_one_or_none()
        if not audit:
            return jsonify({"error": {"code": "not_found", "message": "Audit not found."}}), 404
        issues = (await db.execute(select(AuditIssue).where(AuditIssue.audit_id == audit.id))).scalars().all()
        return jsonify({"id": str(audit.id), "status": audit.status, "overallScore": audit.overall_score, "categoryScores": audit.category_scores, "issues": [{"ruleId": issue.rule_id, "category": issue.category, "severity": issue.severity, "affectedUrl": issue.affected_url, "explanation": issue.explanation, "fixRecommendation": issue.fix_recommendation, "evidence": issue.evidence} for issue in issues]})
