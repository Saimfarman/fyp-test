import csv
import hashlib
import io
import json
import secrets
from datetime import UTC, datetime
from urllib.parse import urlparse

from quart import Blueprint, Response, current_app, g, jsonify, request
from sqlalchemy import select

from .models import ApiKey, Audit, Lead, LeadAssignment, OptOutRequest, OutboxEvent, PipelineActivity, PipelineCard, FollowUp, WebhookDelivery, WebhookEndpoint, WorkspaceMember

bp = Blueprint("platform", __name__, url_prefix="/api")
STAGES = {"NEW", "CONTACTED", "PITCHED", "NEGOTIATING", "WON", "LOST"}
WEBHOOK_EVENTS = {"lead.discovered", "website.classified", "audit.completed", "pitch.viewed", "pipeline.stage_changed", "prototype.export_completed"}
API_SCOPES = {"leads:read", "audits:read", "pitches:write", "webhooks:manage"}


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


async def _workspace_id():
    if not g.user:
        return None
    async with current_app.session_factory() as db:
        member = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == g.user.id).order_by(WorkspaceMember.id))).scalars().first()
        return member.workspace_id if member else None


def _card_json(card, lead=None):
    return {
        "id": str(card.id),
        "leadId": str(card.lead_id),
        "leadName": lead.name if lead else None,
        "stage": card.stage,
        "notes": card.notes,
        "assignedTo": str(card.assigned_to) if card.assigned_to else None,
        "updatedAt": card.updated_at.isoformat() if card.updated_at else None,
    }


async def _api_scope(scope):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    key_hash = hashlib.sha256(authorization[7:].strip().encode()).hexdigest()
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None)))).scalar_one_or_none()
        if not item or scope not in item.scopes:
            return None
        return item.workspace_id


async def _queue_webhook_deliveries(db, workspace_id, event):
    endpoints = (await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace_id, WebhookEndpoint.active.is_(True)))).scalars()
    for endpoint in endpoints:
        if endpoint.events and event.event_name not in endpoint.events:
            continue
        db.add(WebhookDelivery(workspace_id=workspace_id, webhook_id=endpoint.id, event_id=event.id))


@bp.get("/pipeline/cards")
async def list_pipeline_cards():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        rows = (await db.execute(select(PipelineCard, Lead).join(Lead, Lead.id == PipelineCard.lead_id).where(PipelineCard.workspace_id == workspace_id).order_by(PipelineCard.updated_at.desc()))).all()
        return jsonify({"items": [_card_json(card, lead) for card, lead in rows]})


@bp.post("/leads/<uuid:lead_id>/pipeline")
async def save_pipeline_card(lead_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    stage = str(payload.get("stage", "NEW")).upper()
    if stage not in STAGES:
        return _error("validation_error", "Unknown pipeline stage.", 400)
    async with current_app.session_factory() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id))).scalar_one_or_none()
        if not lead:
            return _error("not_found", "Lead not found.", 404)
        card = (await db.execute(select(PipelineCard).where(PipelineCard.lead_id == lead_id, PipelineCard.workspace_id == workspace_id))).scalar_one_or_none()
        previous = card.stage if card else None
        if not card:
            card = PipelineCard(workspace_id=workspace_id, lead_id=lead_id)
            db.add(card)
            await db.flush()
        card.stage = stage
        card.notes = str(payload.get("notes", card.notes))[:4000]
        action = "stage_changed" if previous and previous != stage else "updated"
        db.add(PipelineActivity(workspace_id=workspace_id, card_id=card.id, user_id=g.user.id, action=action, event_metadata={"from": previous, "to": stage}))
        if action == "stage_changed":
            event = OutboxEvent(workspace_id=workspace_id, event_name="pipeline.stage_changed", payload={"leadId": str(lead_id), "from": previous, "to": stage})
            db.add(event)
            await db.flush()
            await _queue_webhook_deliveries(db, workspace_id, event)
        await db.commit()
        return jsonify(_card_json(card, lead))


@bp.post("/pipeline/cards/<uuid:card_id>/move")
async def move_pipeline_card(card_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        card = (await db.execute(select(PipelineCard).where(PipelineCard.id == card_id, PipelineCard.workspace_id == workspace_id))).scalar_one_or_none()
        if not card:
            return _error("not_found", "Pipeline card not found.", 404)
        lead = (await db.execute(select(Lead).where(Lead.id == card.lead_id))).scalar_one()
        stage = str(payload.get("stage", "")).upper()
        if stage not in STAGES:
            return _error("validation_error", "Unknown pipeline stage.", 400)
        previous = card.stage
        card.stage = stage
        db.add(PipelineActivity(workspace_id=workspace_id, card_id=card.id, user_id=g.user.id, action="stage_changed", event_metadata={"from": previous, "to": stage}))
        event = OutboxEvent(workspace_id=workspace_id, event_name="pipeline.stage_changed", payload={"leadId": str(lead.id), "from": previous, "to": stage})
        db.add(event)
        await db.flush()
        await _queue_webhook_deliveries(db, workspace_id, event)
        await db.commit()
        return jsonify(_card_json(card, lead))


@bp.get("/pipeline/cards/<uuid:card_id>/activities")
async def pipeline_activities(card_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        card = (await db.execute(select(PipelineCard).where(PipelineCard.id == card_id, PipelineCard.workspace_id == workspace_id))).scalar_one_or_none()
        if not card:
            return _error("not_found", "Pipeline card not found.", 404)
        rows = (await db.execute(select(PipelineActivity).where(PipelineActivity.card_id == card_id).order_by(PipelineActivity.created_at.desc()))).scalars()
        return jsonify({"items": [{"id": str(row.id), "action": row.action, "metadata": row.event_metadata, "createdAt": row.created_at.isoformat() if row.created_at else None} for row in rows]})


@bp.route("/follow-ups", methods=["GET", "POST"])
async def follow_ups():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        if request.method == "GET":
            rows = (await db.execute(select(FollowUp).where(FollowUp.workspace_id == workspace_id).order_by(FollowUp.due_at))).scalars()
            return jsonify({"items": [{"id": str(row.id), "leadId": str(row.lead_id), "dueAt": row.due_at.isoformat(), "note": row.note, "completed": row.completed_at is not None} for row in rows]})
        payload = await request.get_json(silent=True) or {}
        try:
            due_at = datetime.fromisoformat(str(payload["dueAt"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            return _error("validation_error", "dueAt must be an ISO timestamp.", 400)
        lead_id = payload.get("leadId")
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id))).scalar_one_or_none()
        if not lead:
            return _error("not_found", "Lead not found.", 404)
        item = FollowUp(workspace_id=workspace_id, lead_id=lead.id, due_at=due_at, note=str(payload.get("note", ""))[:1000])
        db.add(item)
        await db.commit()
        return jsonify({"id": str(item.id), "leadId": str(item.lead_id), "dueAt": item.due_at.isoformat(), "note": item.note}), 201


@bp.route("/leads/<uuid:lead_id>/assignments", methods=["GET", "POST"])
async def assign_lead(lead_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        if request.method == "GET":
            rows = (await db.execute(select(LeadAssignment).where(LeadAssignment.lead_id == lead_id, LeadAssignment.workspace_id == workspace_id))).scalars()
            return jsonify({"items": [{"id": str(row.id), "userId": str(row.user_id)} for row in rows]})
        member = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == payload.get("userId")))).scalar_one_or_none()
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id))).scalar_one_or_none()
        if not member or not lead:
            return _error("not_found", "Lead or workspace member not found.", 404)
        assignment = LeadAssignment(workspace_id=workspace_id, lead_id=lead_id, user_id=member.user_id)
        db.add(assignment)
        await db.commit()
        return jsonify({"id": str(assignment.id), "leadId": str(lead_id), "userId": str(member.user_id)}), 201


@bp.delete("/leads/<uuid:lead_id>/assignments/<uuid:user_id>")
async def remove_lead_assignment(lead_id, user_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        assignment = (await db.execute(select(LeadAssignment).where(LeadAssignment.lead_id == lead_id, LeadAssignment.user_id == user_id, LeadAssignment.workspace_id == workspace_id))).scalar_one_or_none()
        if not assignment:
            return _error("not_found", "Assignment not found.", 404)
        await db.delete(assignment)
        await db.commit()
        return jsonify({"ok": True})


@bp.get("/reports/overview")
async def report_overview():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        leads = list((await db.execute(select(Lead).where(Lead.workspace_id == workspace_id))).scalars())
        cards = list((await db.execute(select(PipelineCard).where(PipelineCard.workspace_id == workspace_id))).scalars())
        stages = {stage: sum(1 for card in cards if card.stage == stage) for stage in sorted(STAGES)}
        categories = {}
        cities = {}
        for lead in leads:
            if lead.category:
                categories[lead.category] = categories.get(lead.category, 0) + 1
            city = (lead.address or "").split(",")[-1].strip()
            if city:
                cities[city] = cities.get(city, 0) + 1
        return jsonify({"leads": len(leads), "pipeline": stages, "topCategories": dict(sorted(categories.items(), key=lambda item: item[1], reverse=True)[:10]), "topCities": dict(sorted(cities.items(), key=lambda item: item[1], reverse=True)[:10])})


@bp.get("/exports/leads.csv")
async def export_leads():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        leads = (await db.execute(select(Lead).where(Lead.workspace_id == workspace_id).order_by(Lead.created_at))).scalars()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "name", "category", "address", "phone", "website_url", "status", "severity", "opportunity_score"])
        for lead in leads:
            writer.writerow([lead.id, lead.name, lead.category, lead.address, lead.phone, lead.website_url, lead.website_status, lead.severity, lead.opportunity_score])
        return Response(output.getvalue(), content_type="text/csv", headers={"Content-Disposition": "attachment; filename=leadpitch-leads.csv"})


@bp.get("/exports/audits.json")
async def export_audits():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        audits = (await db.execute(select(Audit).where(Audit.workspace_id == workspace_id).order_by(Audit.created_at))).scalars()
        return jsonify({"items": [{"id": str(audit.id), "leadId": str(audit.lead_id), "status": audit.status, "overallScore": audit.overall_score, "categoryScores": audit.category_scores, "createdAt": audit.created_at.isoformat() if audit.created_at else None} for audit in audits]})


@bp.post("/api-keys")
async def create_api_key():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    scopes = [str(scope) for scope in payload.get("scopes", ["leads:read"]) if str(scope)]
    raw = f"lp_{secrets.token_urlsafe(32)}"
    async with current_app.session_factory() as db:
        item = ApiKey(workspace_id=workspace_id, name=str(payload.get("name", "API key"))[:120], key_hash=hashlib.sha256(raw.encode()).hexdigest(), key_prefix=raw[:10], scopes=scopes)
        db.add(item)
        await db.commit()
        return jsonify({"id": str(item.id), "name": item.name, "prefix": item.key_prefix, "scopes": scopes, "key": raw}), 201


@bp.get("/api-keys")
async def list_api_keys():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        rows = (await db.execute(select(ApiKey).where(ApiKey.workspace_id == workspace_id).order_by(ApiKey.created_at.desc()))).scalars()
        return jsonify({"items": [{"id": str(row.id), "name": row.name, "prefix": row.key_prefix, "scopes": row.scopes, "revoked": row.revoked_at is not None, "createdAt": row.created_at.isoformat() if row.created_at else None} for row in rows]})


@bp.delete("/api-keys/<uuid:key_id>")
async def revoke_api_key(key_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        item = (await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "API key not found.", 404)
        item.revoked_at = datetime.now(UTC)
        await db.commit()
        return jsonify({"ok": True})


@bp.route("/webhooks", methods=["GET", "POST"])
async def webhooks():
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        if request.method == "GET":
            rows = (await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace_id).order_by(WebhookEndpoint.created_at.desc()))).scalars()
            return jsonify({"items": [{"id": str(row.id), "url": row.url, "events": row.events, "active": row.active, "createdAt": row.created_at.isoformat() if row.created_at else None} for row in rows]})
        payload = await request.get_json(silent=True) or {}
        url = str(payload.get("url", "")).strip()
        parsed = urlparse(url)
        events = [str(event) for event in payload.get("events", []) if str(event) in WEBHOOK_EVENTS]
        if parsed.scheme != "https" or not parsed.netloc or not events:
            return _error("validation_error", "An HTTPS URL and at least one supported event are required.", 400)
        secret = secrets.token_urlsafe(32)
        item = WebhookEndpoint(workspace_id=workspace_id, url=url, secret_hash=hashlib.sha256(secret.encode()).hexdigest(), events=events)
        db.add(item)
        await db.commit()
        return jsonify({"id": str(item.id), "url": url, "events": events, "secret": secret}), 201


@bp.delete("/webhooks/<uuid:webhook_id>")
async def delete_webhook(webhook_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        item = (await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace_id))).scalar_one_or_none()
        if not item:
            return _error("not_found", "Webhook not found.", 404)
        await db.delete(item)
        await db.commit()
        return jsonify({"ok": True})


@bp.post("/webhooks/<uuid:webhook_id>/test")
async def test_webhook(webhook_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        webhook = (await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace_id))).scalar_one_or_none()
        if not webhook:
            return _error("not_found", "Webhook not found.", 404)
        event = OutboxEvent(workspace_id=workspace_id, event_name="webhook.test", payload={"message": "LeadPitch webhook test"})
        db.add(event)
        await db.flush()
        delivery = WebhookDelivery(workspace_id=workspace_id, webhook_id=webhook.id, event_id=event.id)
        db.add(delivery)
        await db.commit()
        return jsonify({"id": str(delivery.id), "status": delivery.status}), 202


@bp.get("/webhooks/<uuid:webhook_id>/deliveries")
async def webhook_deliveries(webhook_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        webhook = (await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id, WebhookEndpoint.workspace_id == workspace_id))).scalar_one_or_none()
        if not webhook:
            return _error("not_found", "Webhook not found.", 404)
        rows = (await db.execute(select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id).order_by(WebhookDelivery.created_at.desc()))).scalars()
        return jsonify({"items": [{"id": str(row.id), "status": row.status, "attempts": row.attempts, "lastError": row.last_error} for row in rows]})


@bp.post("/opt-out-requests")
async def opt_out_request():
    payload = await request.get_json(silent=True) or {}
    business_name = str(payload.get("businessName", "")).strip()
    if not business_name:
        return _error("validation_error", "businessName is required.", 400)
    async with current_app.session_factory() as db:
        item = OptOutRequest(
            business_name=business_name[:240],
            website_url=str(payload.get("websiteUrl", "")).strip()[:500] or None,
            contact_email=str(payload.get("contactEmail", "")).strip()[:320] or None,
            reason=str(payload.get("reason", ""))[:2000],
        )
        db.add(item)
        await db.commit()
        return jsonify({"id": str(item.id), "status": item.status}), 202


@bp.get("/v1/leads")
async def versioned_leads():
    workspace_id = await _api_scope("leads:read")
    if not workspace_id:
        return _error("forbidden", "A valid API key with leads:read is required.", 403)
    async with current_app.session_factory() as db:
        leads = (await db.execute(select(Lead).where(Lead.workspace_id == workspace_id).order_by(Lead.created_at.desc()).limit(100))).scalars()
        return jsonify({"items": [{"id": str(lead.id), "name": lead.name, "status": lead.website_status, "severity": lead.severity, "opportunityScore": lead.opportunity_score} for lead in leads]})


@bp.get("/v1/audits")
async def versioned_audits():
    workspace_id = await _api_scope("audits:read")
    if not workspace_id:
        return _error("forbidden", "A valid API key with audits:read is required.", 403)
    async with current_app.session_factory() as db:
        audits = (await db.execute(select(Audit).where(Audit.workspace_id == workspace_id).order_by(Audit.created_at.desc()).limit(100))).scalars()
        return jsonify({"items": [{"id": str(audit.id), "leadId": str(audit.lead_id), "score": audit.overall_score, "status": audit.status} for audit in audits]})


@bp.get("/openapi.json")
async def openapi():
    return jsonify({
        "openapi": "3.0.3",
        "info": {"title": "LeadPitch API", "version": "1.0.0"},
        "paths": {
            "/api/v1/leads": {"get": {"security": [{"ApiKey": []}], "responses": {"200": {"description": "Workspace leads"}}}},
            "/api/v1/audits": {"get": {"security": [{"ApiKey": []}], "responses": {"200": {"description": "Workspace audits"}}}},
            "/api/exports/leads.csv": {"get": {"responses": {"200": {"description": "CSV export"}}}},
            "/api/webhooks": {"get": {"responses": {"200": {"description": "Webhook subscriptions"}}}},
        },
        "components": {"securitySchemes": {"ApiKey": {"type": "http", "scheme": "bearer"}}},
    })
