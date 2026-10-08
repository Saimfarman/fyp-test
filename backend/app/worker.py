import os
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select

from .config import Settings
from .db import create_session_factory
from .models import OutboxEvent, WebhookDelivery, WebhookEndpoint


async def health_job(ctx):
    return {"status": "ok"}


async def deliver_webhooks(ctx):
    factory = create_session_factory(Settings.from_env())
    async with factory() as db:
        rows = (await db.execute(
            select(WebhookDelivery, WebhookEndpoint, OutboxEvent)
            .join(WebhookEndpoint, WebhookEndpoint.id == WebhookDelivery.webhook_id)
            .join(OutboxEvent, OutboxEvent.id == WebhookDelivery.event_id)
            .where(WebhookDelivery.status == "PENDING", WebhookDelivery.next_attempt_at <= datetime.now(UTC))
            .limit(20)
        )).all()
        delivered = 0
        for delivery, endpoint, event in rows:
            delivery.attempts += 1
            body = json.dumps({"id": str(event.id), "event": event.event_name, "data": event.payload}, separators=(",", ":"))
            signature = hmac.new(endpoint.secret_hash.encode(), body.encode(), hashlib.sha256).hexdigest()
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(endpoint.url, content=body, headers={"Content-Type": "application/json", "X-LeadPitch-Signature": f"sha256={signature}", "X-LeadPitch-Event": event.event_name})
                    response.raise_for_status()
                delivery.status = "DELIVERED"
                delivered += 1
            except (httpx.HTTPError, OSError) as error:
                delivery.last_error = str(error)[:500]
                if delivery.attempts >= 5:
                    delivery.status = "FAILED"
                else:
                    delivery.next_attempt_at = datetime.now(UTC) + timedelta(minutes=2 ** delivery.attempts)
        await db.commit()
        return {"delivered": delivered, "checked": len(rows)}


class WorkerSettings:
    functions = [health_job, deliver_webhooks]
    cron_jobs = [cron(deliver_webhooks, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})]
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    max_jobs = 10
