# Production deployment

LeadPitch is packaged as stateless frontend/API containers plus PostgreSQL and
Redis persistent services. Put the frontend and API behind a TLS reverse proxy
such as Caddy or Nginx, set `FRONTEND_ORIGIN` to the public browser origin, and
set `SESSION_COOKIE_SECURE=true`.

1. Copy `.env.example` to `.env` and replace `SECRET_KEY` with at least 32
   random characters.
2. Configure production database and Redis credentials rather than the local
   development defaults.
3. Start the stack with:

```text
docker compose -f compose.yml -f compose.prod.yml up --build -d
```

The migration command runs before the API starts. Back up the PostgreSQL
volume before upgrades. Redis is used for the worker queue; the current MVP
rate limiter is process-local, so a horizontally scaled deployment should add
proxy-level rate limiting or move the bucket store to Redis before exposing
developer API keys publicly.

Readiness is available at `/health/ready`, and liveness at `/health/live`.
Use those endpoints for container and reverse-proxy health checks. API keys
are shown only once at creation, webhook secrets are hashed, and all exports
are workspace-scoped.
