import io
import json
import re
import zipfile
from datetime import datetime
from html import escape

from quart import Blueprint, Response, current_app, g, jsonify, request
from sqlalchemy import select

from .models import Lead, Prototype, PrototypeExport, PrototypeVersion, WorkspaceMember

bp = Blueprint("prototypes", __name__, url_prefix="/api")

TEMPLATES = {
    "local-service": {
        "name": "Local service",
        "description": "A conversion-focused homepage for salons, clinics, restaurants, and local services.",
        "version": "1.0.0",
        "sections": ["hero", "services", "trust", "contact"],
    },
    "retail": {
        "name": "Local retail",
        "description": "A product-forward homepage with location and enquiry calls to action.",
        "version": "1.0.0",
        "sections": ["hero", "services", "trust", "contact"],
    },
    "professional": {
        "name": "Professional practice",
        "description": "A calm, credible presentation for consultants and professional practices.",
        "version": "1.0.0",
        "sections": ["hero", "services", "trust", "contact"],
    },
}


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


async def _workspace_id():
    if not g.user:
        return None
    async with current_app.session_factory() as db:
        member = (await db.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == g.user.id).order_by(WorkspaceMember.id))).scalars().first()
        return member.workspace_id if member else None


def _clean_text(value, limit=500):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _template_payload(template_id):
    template = TEMPLATES.get(template_id)
    if not template:
        return None
    return {"id": template_id, **template}


def _content(lead: Lead, template_id: str) -> dict:
    template = TEMPLATES[template_id]
    return {
        "theme": {"primary": "#152238", "accent": "#ef8354"},
        "business": {
            "name": _clean_text(lead.name, 160),
            "category": _clean_text(lead.category or "Local business", 120),
            "address": _clean_text(lead.address or "Serving your local area", 240),
            "phone": _clean_text(lead.phone or ""),
        },
        "sections": [
            {"id": "hero", "type": "hero", "heading": f"{lead.name}", "subheading": f"Trusted {lead.category or 'local business'} in your area.", "cta": "Get in touch"},
            {"id": "services", "type": "services", "heading": "How we can help", "items": ["Quality service", "Friendly local support", "A simple way to get started"]},
            {"id": "trust", "type": "trust", "heading": "Why choose us", "body": "Clear information, dependable service, and a team ready to help."},
            {"id": "contact", "type": "contact", "heading": "Let’s talk", "body": _clean_text(lead.address or "Contact us to learn more.", 240), "phone": _clean_text(lead.phone or "")},
        ],
        "template": {"id": template_id, "version": template["version"], "sections": template["sections"]},
    }


def _prototype(item: Prototype, lead: Lead):
    return {"id": str(item.id), "lead": {"id": str(lead.id), "name": lead.name}, "templateId": item.template_id, "templateVersion": item.template_version, "status": item.status, "content": item.content, "createdAt": item.created_at.isoformat() if item.created_at else None}


def _html(prototype: Prototype) -> str:
    content = prototype.content
    business = content["business"]
    theme = content["theme"]
    sections = []
    for section in content["sections"]:
        heading = escape(_clean_text(section.get("heading"), 160))
        if section["type"] == "hero":
            body = f"<p>{escape(_clean_text(section.get('subheading'), 300))}</p><a class=\"button\" href=\"#contact\">{escape(_clean_text(section.get('cta'), 80))}</a>"
        elif section["type"] == "services":
            items = "".join(f"<li>{escape(_clean_text(item, 120))}</li>" for item in section.get("items", []))
            body = f"<ul>{items}</ul>"
        else:
            body = f"<p>{escape(_clean_text(section.get('body'), 400))}</p>"
            if section.get("phone"):
                body += f"<p><a href=\"tel:{escape(_clean_text(section['phone'], 40))}\">{escape(_clean_text(section['phone'], 40))}</a></p>"
        sections.append(f"<section id=\"{escape(section['id'])}\"><h2>{heading}</h2>{body}</section>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(business['name'])}</title><style>:root{{--primary:{escape(theme['primary'])};--accent:{escape(theme['accent'])}}}*{{box-sizing:border-box}}body{{margin:0;font:16px system-ui;color:var(--primary);background:#f6f8fb}}main{{max-width:900px;margin:auto;padding:24px}}section{{background:#fff;border-radius:16px;padding:32px;margin:16px 0;box-shadow:0 8px 30px #15223812}}h1{{font-size:clamp(2.5rem,8vw,5rem);margin:.2em 0}}h2{{color:var(--primary)}}.button{{display:inline-block;background:var(--accent);color:#fff;padding:12px 18px;border-radius:8px;text-decoration:none}}li{{margin:.5rem 0}}</style></head><body><main><header><p>{escape(business['category'])}</p><h1>{escape(business['name'])}</h1><p>{escape(business['address'])}</p></header>{''.join(sections)}</main></body></html>"""


@bp.get("/prototype-templates")
async def list_templates():
    return jsonify({"items": [_template_payload(template_id) for template_id in TEMPLATES]})


@bp.post("/leads/<uuid:lead_id>/prototypes")
async def create_prototype(lead_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    template_id = str(payload.get("templateId", "local-service"))
    if template_id not in TEMPLATES:
        return _error("validation_error", "Unknown prototype template.", 400)
    async with current_app.session_factory() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id, Lead.workspace_id == workspace_id))).scalar_one_or_none()
        if not lead:
            return _error("not_found", "Lead not found.", 404)
        item = Prototype(workspace_id=workspace_id, lead_id=lead.id, template_id=template_id, template_version=TEMPLATES[template_id]["version"], content=_content(lead, template_id))
        db.add(item)
        await db.flush()
        db.add(PrototypeVersion(prototype_id=item.id, version_number=1, content=item.content))
        await db.commit()
        return jsonify(_prototype(item, lead)), 201


async def _owned(db, prototype_id, workspace_id):
    return (await db.execute(select(Prototype, Lead).join(Lead, Lead.id == Prototype.lead_id).where(Prototype.id == prototype_id, Prototype.workspace_id == workspace_id))).first()


def _export_payload(item: PrototypeExport):
    return {
        "id": str(item.id),
        "prototypeId": str(item.prototype_id),
        "framework": item.framework,
        "status": item.status,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
    }


def _archive(item: Prototype, framework: str) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr("README.md", "# LeadPitch prototype\n\nGenerated from an editable LeadPitch template.\n")
        output.writestr("index.html", _html(item))
        output.writestr("prototype.json", json.dumps(item.content, indent=2))
        if framework == "react":
            output.writestr("src/App.jsx", "export default function App() { return <iframe title=\"Prototype preview\" src=\"../index.html\" />; }\n")
            output.writestr("package.json", '{"scripts":{"dev":"vite"},"dependencies":{"react":"latest","react-dom":"latest","vite":"latest"}}\n')
    return archive.getvalue()


async def _owned_export(db, export_id, workspace_id):
    return (await db.execute(
        select(PrototypeExport, Prototype)
        .join(Prototype, Prototype.id == PrototypeExport.prototype_id)
        .where(PrototypeExport.id == export_id, Prototype.workspace_id == workspace_id)
    )).first()


@bp.get("/prototype-exports/<uuid:export_id>")
async def get_prototype_export(export_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = await _owned_export(db, export_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype export not found.", 404)
        return jsonify(_export_payload(row.PrototypeExport))


@bp.get("/prototype-exports/<uuid:export_id>/download")
async def download_prototype_export(export_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = await _owned_export(db, export_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype export not found.", 404)
        export, item = row
        return Response(
            _archive(item, export.framework),
            content_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="leadpitch-{item.id}.zip"'},
        )


@bp.get("/prototypes/<uuid:prototype_id>")
async def get_prototype(prototype_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = await _owned(db, prototype_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype not found.", 404)
        return jsonify(_prototype(row.Prototype, row.Lead))


@bp.patch("/prototypes/<uuid:prototype_id>")
async def update_prototype(prototype_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        row = await _owned(db, prototype_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype not found.", 404)
        item, lead = row
        content = dict(item.content)
        if isinstance(payload.get("theme"), dict):
            theme = dict(content.get("theme", {}))
            for key in ("primary", "accent"):
                if key in payload["theme"] and re.fullmatch(r"#[0-9a-fA-F]{6}", str(payload["theme"][key])):
                    theme[key] = payload["theme"][key]
            content["theme"] = theme
        if isinstance(payload.get("sections"), list):
            allowed = {section["id"]: section for section in content["sections"]}
            for incoming in payload["sections"]:
                if not isinstance(incoming, dict) or incoming.get("id") not in allowed:
                    continue
                section = allowed[incoming["id"]]
                for key in ("heading", "subheading", "cta", "body"):
                    if key in incoming:
                        section[key] = _clean_text(incoming[key])
                if isinstance(incoming.get("items"), list):
                    section["items"] = [_clean_text(value, 120) for value in incoming["items"][:8]]
            content["sections"] = list(allowed.values())
        item.content = content
        latest = (await db.execute(select(PrototypeVersion).where(PrototypeVersion.prototype_id == item.id).order_by(PrototypeVersion.version_number.desc()))).scalars().first()
        db.add(PrototypeVersion(prototype_id=item.id, version_number=(latest.version_number + 1 if latest else 1), content=content))
        await db.commit()
        return jsonify(_prototype(item, lead))


@bp.get("/prototypes/<uuid:prototype_id>/preview")
async def preview_prototype(prototype_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    async with current_app.session_factory() as db:
        row = await _owned(db, prototype_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype not found.", 404)
        return Response(_html(row.Prototype), content_type="text/html")


@bp.post("/prototypes/<uuid:prototype_id>/export")
async def export_prototype(prototype_id):
    workspace_id = await _workspace_id()
    if not workspace_id:
        return _error("unauthenticated", "Authentication required.", 401)
    payload = await request.get_json(silent=True) or {}
    framework = str(payload.get("framework", "html")).lower()
    if framework not in {"html", "react"}:
        return _error("validation_error", "framework must be html or react.", 400)
    async with current_app.session_factory() as db:
        row = await _owned(db, prototype_id, workspace_id)
        if not row:
            return _error("not_found", "Prototype not found.", 404)
        item, _ = row
        db.add(PrototypeExport(prototype_id=item.id, framework=framework))
        await db.commit()
        return Response(_archive(item, framework), content_type="application/zip", headers={"Content-Disposition": f'attachment; filename="leadpitch-{item.id}.zip"'})
