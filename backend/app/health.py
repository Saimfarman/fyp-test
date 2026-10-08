from quart import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

bp = Blueprint("health", __name__)


@bp.get("/health/live")
async def live():
    return jsonify({"status": "ok"})


@bp.get("/health/ready")
async def ready():
    try:
        async with current_app.session_factory() as db:
            await db.execute(text("SELECT 1"))
        return jsonify({"status": "ready", "checks": {"database": "ok"}})
    except (SQLAlchemyError, OSError, RuntimeError):
        return jsonify({"error": {"code": "not_ready", "message": "Dependencies are unavailable."}}), 503
