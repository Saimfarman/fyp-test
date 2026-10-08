# LeadPitch

LeadPitch helps digital-service sellers discover local businesses in Pakistan
that lack a website or need practical website, SEO, and marketing improvements.
It combines responsible local-business discovery, explainable website audits,
bilingual outreach, proposal generation, and editable website prototypes.

## Phase 7 status

The Phase 4 audit foundation is implemented on top of Phase 3: Docker Compose
definitions, an async Quart backend, PostgreSQL migrations, Redis/arq wiring,
session authentication, workspace/role/credit foundations, health endpoints,
and a Next.js frontend shell. OSM discovery, website classification, CSV
import, lead APIs, and the responsive discovery workspace are now included,
along with a bounded SSRF-aware website audit engine, plugin rules, scoring,
issue persistence, and audit summary UI. Phase 5 now adds deterministic
English/Urdu pitch drafts, service catalog/package APIs, proposal PDFs, opaque
share links with expiry/revocation, public proposal projections, and a pitch
builder view. Phase 6 now adds versioned industry templates, data-bound
prototype creation, constrained text/theme editing, responsive desktop/tablet/
mobile preview, sanitized HTML generation, and HTML/React project ZIP
exports. Phase 7 adds the pipeline/activity and developer export/API-key/
webhook surfaces, production rate limiting and readiness checks, an
installable offline-capable PWA shell, CI, and production deployment notes.
Remaining platform hardening now also includes a responsive pipeline board,
scoped `/api/v1` lead/audit endpoints, OpenAPI metadata, queued signed webhook
delivery with retries, follow-ups, assignments, reporting, and opt-out
suppression during discovery.

The implementation remains gated by the phase sequence in
[docs/architecture.md](docs/architecture.md#implementation-phases).

Read these documents in order:

1. [Product scope](docs/product-scope.md) — MVP/later boundaries by audience.
2. [Architecture](docs/architecture.md) — system design, data model, scoring,
   UI wireframes, deployment, risks, and milestones.
3. [API overview](docs/api-overview.md) — endpoint groups, payload contracts,
   events, authorization, and error handling.

Open `/discover` after signing in to search an OSM-compatible area and review
the lead list, severity-aware pins, and detail drawer. OSM attribution is shown
on the discovery surface. The current map surface is an adapter-safe MVP
renderer; a production tile renderer can be connected without changing the
discovery API.

Phase 2 local prerequisites:

- Docker Desktop with the Linux engine running.
- Node.js 22+ for the frontend.
- Python 3.12+ when running the backend outside Docker.

Once Docker is running, start the foundation with:

```text
docker compose up --build
```

The backend applies all ordered SQL migrations, including the Phase 4 audit
schema, Phase 5 pitch schema, and Phase 6 prototype schema in
`backend/migrations/003_audits.sql`, `backend/migrations/004_pitches.sql`, and
`backend/migrations/005_prototypes.sql`, before starting.
The final platform schema is in `backend/migrations/006_platform.sql`.

Production deployment instructions are in
[docs/deployment.md](docs/deployment.md).

## Confirmed product decisions

- **Platform:** responsive web application and installable PWA, not a native app.
- **Discovery:** OpenStreetMap, Overpass API, and Nominatim for MVP; no Google
  Cloud subscription or Google Maps scraping is required.
- **Hosting:** local Docker development and generic VPS-compatible deployment.
- **Generation:** deterministic templates first, with optional provider
  interfaces for a future LLM; generated content must remain fact-grounded.
- **Authentication:** email/password with secure HTTP-only session cookies;
  OAuth is deferred.
- **Billing:** checkout is deferred, but internal free/pro/team plans and
  credits are enforced in the MVP design.

## Planned local development

The implementation will provide a one-command Docker workflow:

```text
docker compose up
```

The planned services are a reverse proxy, frontend, Quart API, background
worker, PostgreSQL, and Redis. Exact commands and environment variables will be
added during Phase 2 together with `.env.example` and health checks.

## Responsible use

LeadPitch must use official/public data sources, respect OSM attribution and
provider usage policies, obey `robots.txt` and crawl limits, avoid automated
spam, and provide a business opt-out/removal process. Public pitch links must
not expose private workspace notes or contact history.
