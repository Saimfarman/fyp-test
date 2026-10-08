import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from quart import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select

from .models import CreditAccount, User, Workspace, WorkspaceInvitation, WorkspaceMember

bp = Blueprint("workspaces", __name__, url_prefix="/api")


def _unauthenticated():
    return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401


async def _membership(db, workspace_id):
    return (await db.execute(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == g.user.id
    ))).scalar_one_or_none()


def _workspace_json(workspace, role=None):
    return {
        "id": str(workspace.id), "name": workspace.name, "plan": workspace.plan,
        "role": role, "companyName": workspace.company_name or workspace.name,
        "logoUrl": workspace.logo_url, "brandColor": workspace.brand_color,
        "defaultCity": workspace.default_city, "customDomain": workspace.custom_domain,
    }


@bp.get("/workspaces")
async def list_workspaces():
    if not g.user:
        return _unauthenticated()
    async with current_app.session_factory() as db:
        result = await db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == g.user.id)
            .order_by(Workspace.created_at)
        )
        return jsonify(
            {
                "items": [
                    _workspace_json(workspace, role)
                    for workspace, role in result.all()
                ]
            }
        )


@bp.post("/workspaces")
async def create_workspace():
    if not g.user:
        return _unauthenticated()
    payload = await request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return jsonify({"error": {"code": "validation_error", "message": "Workspace name is required."}}), 400
    async with current_app.session_factory() as db:
        workspace = Workspace(name=name)
        db.add(workspace)
        await db.flush()
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=g.user.id, role="owner"))
        db.add(CreditAccount(workspace_id=workspace.id, balance=100))
        await db.commit()
        return jsonify({"id": str(workspace.id), "name": workspace.name, "plan": workspace.plan, "role": "owner"}), 201


@bp.get("/workspaces/<uuid:workspace_id>/credits")
async def get_credits(workspace_id):
    if not g.user:
        return _unauthenticated()
    async with current_app.session_factory() as db:
        member = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == g.user.id,
                )
            )
        ).scalar_one_or_none()
        if not member:
            return jsonify({"error": {"code": "forbidden", "message": "Workspace access denied."}}), 403
        account = (
            await db.execute(select(CreditAccount).where(CreditAccount.workspace_id == workspace_id))
        ).scalar_one_or_none()
        if not account:
            return jsonify({"error": {"code": "not_found", "message": "Credit account not found."}}), 404
        return jsonify({"workspaceId": str(workspace_id), "balance": account.balance})


@bp.get("/workspaces/<uuid:workspace_id>")
async def get_workspace(workspace_id):
    if not g.user:
        return _unauthenticated()
    async with current_app.session_factory() as db:
        member = await _membership(db, workspace_id)
        if not member:
            return jsonify({"error": {"code": "forbidden", "message": "Workspace access denied."}}), 403
        workspace = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one()
        return jsonify(_workspace_json(workspace, member.role))


@bp.patch("/workspaces/<uuid:workspace_id>")
async def update_workspace(workspace_id):
    if not g.user:
        return _unauthenticated()
    payload = await request.get_json(silent=True) or {}
    async with current_app.session_factory() as db:
        member = await _membership(db, workspace_id)
        if not member or member.role not in {"owner", "manager"}:
            return jsonify({"error": {"code": "forbidden", "message": "Only workspace managers can update settings."}}), 403
        workspace = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
        if not workspace:
            return jsonify({"error": {"code": "not_found", "message": "Workspace not found."}}), 404
        if "name" in payload and str(payload["name"]).strip():
            workspace.name = str(payload["name"]).strip()[:120]
        for key, attr, limit in [("companyName", "company_name", 160), ("logoUrl", "logo_url", 500),
                                 ("defaultCity", "default_city", 80), ("customDomain", "custom_domain", 255)]:
            if key in payload:
                setattr(workspace, attr, str(payload[key]).strip()[:limit] or None)
        if "brandColor" in payload:
            color = str(payload["brandColor"]).strip()
            if len(color) != 7 or not color.startswith("#"):
                return jsonify({"error": {"code": "validation_error", "message": "brandColor must be a six-digit hex color."}}), 400
            workspace.brand_color = color
        await db.commit()
        return jsonify(_workspace_json(workspace, member.role))


@bp.get("/workspaces/<uuid:workspace_id>/members")
async def list_members(workspace_id):
    if not g.user:
        return _unauthenticated()
    async with current_app.session_factory() as db:
        if not await _membership(db, workspace_id):
            return jsonify({"error": {"code": "forbidden", "message": "Workspace access denied."}}), 403
        rows = (await db.execute(select(WorkspaceMember, User).join(User, User.id == WorkspaceMember.user_id)
                                 .where(WorkspaceMember.workspace_id == workspace_id)
                                 .order_by(User.email))).all()
        return jsonify({"items": [{"id": str(member.user_id), "email": user.email, "role": member.role}
                                  for member, user in rows]})


@bp.post("/workspaces/<uuid:workspace_id>/invitations")
async def invite_member(workspace_id):
    if not g.user:
        return _unauthenticated()
    payload = await request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", "sales")).lower()
    if "@" not in email or role not in {"manager", "sales", "developer"}:
        return jsonify({"error": {"code": "validation_error", "message": "A valid email and role are required."}}), 400
    async with current_app.session_factory() as db:
        member = await _membership(db, workspace_id)
        if not member or member.role not in {"owner", "manager"}:
            return jsonify({"error": {"code": "forbidden", "message": "Only workspace managers can invite members."}}), 403
        token = secrets.token_urlsafe(32)
        invitation = WorkspaceInvitation(workspace_id=workspace_id, email=email, role=role,
                                         token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                         expires_at=datetime.now(UTC) + timedelta(days=7))
        db.add(invitation)
        await db.commit()
        return jsonify({"id": str(invitation.id), "email": email, "role": role,
                        "inviteToken": token, "expiresAt": invitation.expires_at.isoformat()}), 201
