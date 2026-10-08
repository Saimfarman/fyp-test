import time
from collections import defaultdict, deque

from quart import Blueprint, current_app, request

bp = Blueprint("security", __name__)


@bp.before_app_request
async def rate_limit_requests():
    if not request.path.startswith("/api/") or request.path.startswith("/api/share/"):
        return None
    now = time.monotonic()
    key = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    buckets = current_app.extensions.setdefault("rate_limit_buckets", defaultdict(deque))
    bucket = buckets[key]
    while bucket and now - bucket[0] >= 60:
        bucket.popleft()
    if len(bucket) >= 120:
        from quart import jsonify
        return jsonify({"error": {"code": "rate_limited", "message": "Too many requests. Try again shortly."}}), 429
    bucket.append(now)
    return None
