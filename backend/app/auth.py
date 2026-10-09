import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from quart import Blueprint, current_app, g, jsonify, request, session
from sqlalchemy import select

from .models import Session, User, Workspace, WorkspaceMember, CreditAccount

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
password_hasher = PasswordHasher()


def _csrf() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@bp.before_app_request
async def load_user() -> None:
    g.user = None
    session_id = session.get("session_id")
    if not session_id:
        return
    async with current_app.session_factory() as db:
        result = await db.execute(select(Session, User).join(User, User.id == Session.user_id).where(Session.id == session_id))
        row = result.first()
        if row and row.Session.expires_at > datetime.now(UTC):
            g.user = row.User


@bp.post("/register")
async def register():
    payload = await request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    workspace_name = str(payload.get("workspaceName", "")).strip()
    if "@" not in email or len(password) < 10 or not workspace_name:
        return jsonify({"error": {"code": "validation_error", "message": "Email, password (10+ characters), and workspace name are required."}}), 400
    async with current_app.session_factory() as db:
        if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            return jsonify({"error": {"code": "conflict", "message": "An account already exists for this email."}}), 409
        user = User(email=email, password_hash=password_hasher.hash(password))
        workspace = Workspace(name=workspace_name)
        db.add_all([user, workspace])
        await db.flush()
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
        db.add(CreditAccount(workspace_id=workspace.id, balance=100))
        await db.commit()
        await _create_session(user.id)
        return jsonify({"user": {"id": str(user.id), "email": user.email}, "workspace": {"id": str(workspace.id), "name": workspace.name}, "csrfToken": _csrf()}), 201


@bp.post("/login")
async def login():
    payload = await request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    async with current_app.session_factory() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            return jsonify({"error": {"code": "unauthenticated", "message": "Invalid email or password."}}), 401
        try:
            password_hasher.verify(user.password_hash, password)
        except VerificationError:
            return jsonify({"error": {"code": "unauthenticated", "message": "Invalid email or password."}}), 401
        await _create_session(user.id)
        return jsonify({"user": {"id": str(user.id), "email": user.email}, "csrfToken": _csrf()})


@bp.post("/logout")
async def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
async def me():
    if not g.user:
        return jsonify({"error": {"code": "unauthenticated", "message": "Authentication required."}}), 401
    return jsonify({"user": {"id": str(g.user.id), "email": g.user.email}, "csrfToken": _csrf()})


async def _create_session(user_id) -> None:
    session_id = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    async with current_app.session_factory() as db:
        db.add(Session(id=session_id, user_id=user_id, csrf_token=csrf_token, expires_at=datetime.now(UTC) + timedelta(days=7)))
        await db.commit()
    session.clear()
    session["session_id"] = session_id
    session["csrf_token"] = csrf_token
