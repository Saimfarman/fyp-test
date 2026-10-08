import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from quart import Blueprint, current_app, g, jsonify, request, Response
from sqlalchemy import select

from .models import (
    Audit,
    AuditIssue,
    Lead,
    PitchDocument,
    PitchRecommendation,
    ServiceCatalogItem,
    ServicePackage,
    ShareLink,
    ShareView,
    WorkspaceMember,
)

bp = Blueprint("pitches", __name__, url_prefix="/api")


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


async def _workspace_id():
    if not g.user:
        return None
    async with current_app.session_factory() as db:
        member = (
            await db.execute(
                select(WorkspaceMember)
                .where(WorkspaceMember.user_id == g.user.id)
                .order_by(WorkspaceMember.id)
            )
        ).scalars().first()
        return member.workspace_id if member else None


async def _lead_for_workspace(db, lead_id, workspace_id):
    return (
        await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()


def _recommendations(lead: Lead, issues: list[AuditIssue]) -> list[dict]:
    recommendations = [
        {
            "phase": "Foundation",
            "title": "Create a fast, mobile-friendly website",
            "description": f"Give {lead.name} a clear home for services, location, contact details, and trust signals.",
            "priority": "HIGH" if lead.website_status in {"NO_WEBSITE", "DEAD_SITE"} else "MEDIUM",
            "sourceIssueIds": [],
        },
        {
            "phase": "Visibility",
            "title": "Improve local SEO",
            "description": "Align the business name, address, phone, page titles, descriptions, and local service content.",
            "priority": "HIGH",
            "sourceIssueIds": [str(issue.id) for issue in issues if issue.category in {"On-page", "Local SEO"}],
        },
        {
            "phase": "Conversion",
            "title": "Add clear contact actions",
            "description": "Make it easy for visitors to call, message on WhatsApp, request a quote, or find the business.",
            "priority": "MEDIUM",
            "sourceIssueIds": [str(issue.id) for issue in issues if issue.category == "Conversion"],
        },
    ]
    return recommendations


def _build_content(lead: Lead, audit: Audit | None, issues: list[AuditIssue], language: str) -> dict:
    score = audit.overall_score if audit else None
    score_line = f"Your current website audit score is {score}/100." if score is not None else "Your business does not currently have a complete website presence."
    english = {
        "opening": f"Hello {lead.name} team,",
        "body": f"We help local businesses turn online searches into real enquiries. {score_line}",
        "value": "We can build a clear, mobile-friendly online presence that explains your services, improves local visibility, and makes it simple for customers to contact you.",
        "callToAction": "Would you be open to a short conversation about a practical improvement plan?",
    }
    urdu = {
        "opening": f"السلام علیکم {lead.name} ٹیم،",
        "body": "ہم مقامی کاروباروں کو آن لائن تلاش کو حقیقی رابطوں میں تبدیل کرنے میں مدد دیتے ہیں۔",
        "value": "ہم آپ کے لیے موبائل پر آسان ویب سائٹ، بہتر لوکل سرچ موجودگی، اور واضح رابطے کے طریقے بنا سکتے ہیں۔",
        "callToAction": "کیا آپ ایک مختصر گفتگو کے لیے دستیاب ہوں گے تاکہ عملی منصوبہ شیئر کیا جا سکے؟",
    }
    return {
        "language": language,
        "english": english,
        "urdu": urdu,
        "score": score,
        "websiteStatus": lead.website_status,
        "recommendations": _recommendations(lead, issues),
        "scope": ["Responsive business website", "Local SEO foundations", "Contact and WhatsApp conversion path"],
        "timeline": "1-2 weeks for an MVP website",
        "price": None,
        "terms": "Final scope and price are confirmed after a short discovery call.",
    }


def _service(item: ServiceCatalogItem) -> dict:
    return {"id": str(item.id), "name": item.name, "description": item.description, "unitPrice": item.unit_price, "currency": item.currency, "active": item.active}


def _package(item: ServicePackage) -> dict:
    return {"id": str(item.id), "name": item.name, "description": item.description, "price": item.price, "currency": item.currency, "serviceIds": item.service_ids, "active": item.active}


def _pitch(pitch: PitchDocument, lead: Lead) -> dict:
    return {"id": str(pitch.id), "lead": {"id": str(lead.id), "name": lead.name}, "title": pitch.title, "language": pitch.language, "status": pitch.status, **pitch.content, "createdAt": pitch.created_at.isoformat() if pitch.created_at else None}


@bp.get("/service-catalog")
async def list_services():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        items = (await db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.workspace_id == workspace_id).order_by(ServiceCatalogItem.name))).scalars().all()
        return jsonify({"items": [_service(item) for item in items]})


@bp.post("/service-catalog")
async def create_service():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return _error("validation_error", "Service name is required.", 400)
    try:
        price = max(0, int(payload.get("unitPrice", 0)))
    except (TypeError, ValueError):
        return _error("validation_error", "unitPrice must be a non-negative integer.", 400)
    async with current_app.session_factory() as db:
        item = ServiceCatalogItem(workspace_id=workspace_id, name=name, description=str(payload.get("description", "")).strip(), unit_price=price, currency=str(payload.get("currency", "PKR")).upper()[:3])
        db.add(item)
        await db.commit()
        return jsonify(_service(item)), 201


@bp.patch("/service-catalog/<uuid:item_id>")
async def update_service(item_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id, ServiceCatalogItem.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "Service not found.", 404)
        if "name" in payload and str(payload["name"]).strip():
            item.name = str(payload["name"]).strip()
        if "description" in payload:
            item.description = str(payload["description"]).strip()
        if "unitPrice" in payload:
            try:
                item.unit_price = max(0, int(payload["unitPrice"]))
            except (TypeError, ValueError):
                return _error("validation_error", "unitPrice must be a non-negative integer.", 400)
        if "active" in payload:
            item.active = bool(payload["active"])
        await db.commit()
        return jsonify(_service(item))


@bp.delete("/service-catalog/<uuid:item_id>")
async def delete_service(item_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.id == item_id, ServiceCatalogItem.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "Service not found.", 404)
        item.active = False
        await db.commit()
        return jsonify({"ok": True})


@bp.get("/service-packages")
async def list_packages():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        items = (await db.execute(select(ServicePackage).where(ServicePackage.workspace_id == workspace_id).order_by(ServicePackage.name))).scalars().all()
        return jsonify({"items": [_package(item) for item in items]})


@bp.post("/service-packages")
async def create_package():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return _error("validation_error", "Package name is required.", 400)
    try:
        price = max(0, int(payload.get("price", 0)))
    except (TypeError, ValueError):
        return _error("validation_error", "price must be a non-negative integer.", 400)
    service_ids = payload.get("serviceIds", [])
    if not isinstance(service_ids, list):
        return _error("validation_error", "serviceIds must be an array.", 400)
    async with current_app.session_factory() as db:
        item = ServicePackage(workspace_id=workspace_id, name=name, description=str(payload.get("description", "")).strip(), price=price, currency=str(payload.get("currency", "PKR")).upper()[:3], service_ids=service_ids)
        db.add(item)
        await db.commit()
        return jsonify(_package(item)), 201


@bp.patch("/service-packages/<uuid:item_id>")
async def update_package(item_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ServicePackage).where(ServicePackage.id == item_id, ServicePackage.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "Package not found.", 404)
        if "name" in payload and str(payload["name"]).strip():
            item.name = str(payload["name"]).strip()
        if "description" in payload:
            item.description = str(payload["description"]).strip()
        if "price" in payload:
            try:
                item.price = max(0, int(payload["price"]))
            except (TypeError, ValueError):
                return _error("validation_error", "price must be a non-negative integer.", 400)
        if "serviceIds" in payload and isinstance(payload["serviceIds"], list):
            item.service_ids = payload["serviceIds"]
        if "active" in payload:
            item.active = bool(payload["active"])
        await db.commit()
        return jsonify(_package(item))


@bp.delete("/service-packages/<uuid:item_id>")
async def delete_package(item_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ServicePackage).where(ServicePackage.id == item_id, ServicePackage.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "Package not found.", 404)
        item.active = False
        await db.commit()
        return jsonify({"ok": True})


@bp.post("/leads/<uuid:lead_id>/pitches")
async def create_pitch(lead_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    language = str(payload.get("language", "both")).lower()
    if language not in {"english", "urdu", "both"}:
        return _error("validation_error", "language must be english, urdu, or both.", 400)
    async with current_app.session_factory() as db:
        lead = await _lead_for_workspace(db, lead_id, workspace_id)
        if not lead:
            return _error("not_found", "Lead not found.", 404)
        audit = (await db.execute(select(Audit).where(Audit.lead_id == lead.id, Audit.workspace_id == workspace_id).order_by(Audit.created_at.desc()))).scalars().first()
        issues = []
        if audit:
            issues = (await db.execute(select(AuditIssue).where(AuditIssue.audit_id == audit.id))).scalars().all()
        selected = payload.get("selectedServiceIds", [])
        selected = selected if isinstance(selected, list) else []
        selected_services = (
            (await db.execute(select(ServiceCatalogItem).where(ServiceCatalogItem.workspace_id == workspace_id, ServiceCatalogItem.id.in_(selected), ServiceCatalogItem.active.is_(True)))).scalars().all()
            if selected
            else []
        )
        content = _build_content(lead, audit, issues, language)
        content["selectedServices"] = [_service(item) for item in selected_services]
        content["estimatedPrice"] = sum(item.unit_price for item in selected_services) or None
        pitch = PitchDocument(workspace_id=workspace_id, lead_id=lead.id, title=f"Website growth plan for {lead.name}", language=language, content=content, selected_service_ids=selected)
        db.add(pitch)
        await db.flush()
        for recommendation in content["recommendations"]:
            db.add(PitchRecommendation(pitch_id=pitch.id, phase=recommendation["phase"], title=recommendation["title"], description=recommendation["description"], priority=recommendation["priority"], source_issue_ids=recommendation["sourceIssueIds"]))
        await db.commit()
        return jsonify(_pitch(pitch, lead)), 201


@bp.get("/pitches/<uuid:pitch_id>")
async def get_pitch(pitch_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = (await db.execute(select(PitchDocument, Lead).join(Lead, Lead.id == PitchDocument.lead_id).where(PitchDocument.id == pitch_id, PitchDocument.workspace_id == workspace_id))).first()
        if not row:
            return _error("not_found", "Pitch not found.", 404)
        return jsonify(_pitch(row.PitchDocument, row.Lead))


@bp.patch("/pitches/<uuid:pitch_id>")
async def update_pitch(pitch_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        row = (await db.execute(select(PitchDocument, Lead).join(Lead, Lead.id == PitchDocument.lead_id).where(PitchDocument.id == pitch_id, PitchDocument.workspace_id == workspace_id))).first()
        if not row:
            return _error("not_found", "Pitch not found.", 404)
        pitch, lead = row
        if "title" in payload and str(payload["title"]).strip():
            pitch.title = str(payload["title"]).strip()
        content = dict(pitch.content or {})
        for key in ("scope", "timeline", "terms"):
            if key in payload and key in pitch.content:
                content[key] = str(payload[key]).strip()
        if isinstance(payload.get("english"), dict):
            content["english"] = {**content.get("english", {}), **payload["english"]}
        if isinstance(payload.get("urdu"), dict):
            content["urdu"] = {**content.get("urdu", {}), **payload["urdu"]}
        pitch.content = content
        if isinstance(payload.get("selectedServiceIds"), list):
            pitch.selected_service_ids = payload["selectedServiceIds"]
        await db.commit()
        return jsonify(_pitch(pitch, lead))


def _pdf_bytes(title: str, lines: list[str]) -> bytes:
    def pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace(")", "\\)").replace("(", "\\(")

    safe_lines = [line.encode("latin-1", "replace").decode("latin-1")[:110] for line in lines]
    stream = ["BT", "/F1 18 Tf", "50 770 Td", f"({pdf_text(title)}) Tj", "/F1 10 Tf"]
    for line in safe_lines:
        stream.append("0 -18 Td")
        stream.append(f"({pdf_text(line)}) Tj")
    stream.append("ET")
    content = "\n".join(stream).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    output += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return output


@bp.route("/pitches/<uuid:pitch_id>/pdf", methods=["GET", "POST"])
async def pitch_pdf(pitch_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = (await db.execute(select(PitchDocument, Lead).join(Lead, Lead.id == PitchDocument.lead_id).where(PitchDocument.id == pitch_id, PitchDocument.workspace_id == workspace_id))).first()
        if not row:
            return _error("not_found", "Pitch not found.", 404)
        content = row.PitchDocument.content
        lines = [content["english"]["body"], content["english"]["value"], "Recommendations:"]
        lines.extend(f"- {item['title']}: {item['description']}" for item in content.get("recommendations", []))
        lines.extend(["Scope: " + ", ".join(content.get("scope", [])), "Timeline: " + str(content.get("timeline", "")), str(content.get("terms", ""))])
        return Response(_pdf_bytes(row.PitchDocument.title, lines), content_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{quote(row.PitchDocument.title)}.pdf"'})


@bp.post("/pitches/<uuid:pitch_id>/share")
async def create_share(pitch_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    days = min(max(int(payload.get("expiresInDays", 30)), 1), 365) if str(payload.get("expiresInDays", "30")).isdigit() else 30
    token = secrets.token_urlsafe(32)
    async with current_app.session_factory() as db:
        pitch = (await db.execute(select(PitchDocument).where(PitchDocument.id == pitch_id, PitchDocument.workspace_id == workspace_id))).scalar_one_or_none()
        if not pitch:
            return _error("not_found", "Pitch not found.", 404)
        link = ShareLink(workspace_id=workspace_id, pitch_id=pitch.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.now(UTC) + timedelta(days=days))
        db.add(link)
        await db.commit()
        return jsonify({"id": str(link.id), "token": token, "expiresAt": link.expires_at.isoformat()}), 201


@bp.delete("/pitches/<uuid:pitch_id>/share/<uuid:share_id>")
async def revoke_share(pitch_id, share_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        link = (await db.execute(select(ShareLink).where(ShareLink.id == share_id, ShareLink.pitch_id == pitch_id, ShareLink.workspace_id == workspace_id))).scalar_one_or_none()
        if not link:
            return _error("not_found", "Share link not found.", 404)
        link.revoked_at = datetime.now(UTC)
        await db.commit()
        return jsonify({"ok": True})


@bp.get("/share/<token>")
async def public_share(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with current_app.session_factory() as db:
        link = (await db.execute(select(ShareLink).where(ShareLink.token_hash == token_hash))).scalar_one_or_none()
        if not link or link.revoked_at or (link.expires_at and link.expires_at <= datetime.now(UTC)):
            return _error("not_found", "This share link is unavailable.", 404)
        row = (await db.execute(select(PitchDocument, Lead).join(Lead, Lead.id == PitchDocument.lead_id).where(PitchDocument.id == link.pitch_id))).first()
        if not row:
            return _error("not_found", "Pitch not found.", 404)
        db.add(ShareView(share_link_id=link.id))
        await db.commit()
        return jsonify({"pitch": _pitch(row.PitchDocument, row.Lead), "public": True})
