from quart import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select

from .models import CreditAccount, Workspace, WorkspaceMember

bp = Blueprint("workspaces", __name__, url_prefix="/api")


def _unauthenticated():
    return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401


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
                    {"id": str(workspace.id), "name": workspace.name, "plan": workspace.plan, "role": role}
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
