# LeadPitch API overview

This document defines the Phase 1 contract direction. Concrete schemas,
authentication middleware, migrations, and generated OpenAPI output are
implemented in later phases.

## Conventions

- Base browser API: `/api`.
- Versioned developer API: `/api/v1`.
- JSON uses camelCase at the public boundary; database naming is internal.
- IDs are opaque UUIDs. Timestamps are ISO 8601 UTC.
- List endpoints return `{ "items": [], "page": { ... } }`.
- Long-running operations return `202 Accepted` with a `jobId`.
- Progress is available at `GET /jobs/{jobId}/events` using SSE.
- All tenant-owned resources require an active workspace context.
- Browser authentication uses a secure HTTP-only session cookie and CSRF token.
- API keys are scoped, rate-limited, and never returned after creation.

## Error envelope

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be accepted.",
    "details": {
      "field": "city",
      "reason": "must be one of the configured cities"
    },
    "requestId": "01J..."
  }
}
```

Expected codes include `unauthenticated`, `forbidden`, `notFound`,
`validationError`, `creditLimitExceeded`, `providerUnavailable`,
`rateLimited`, `jobFailed`, `conflict`, and `internalError`. The API must not
return a success-shaped fallback for a failed provider or job.

## Authentication and workspaces

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a user and initial workspace |
| POST | `/auth/login` | Establish a rotated session |
| POST | `/auth/logout` | Revoke the current session |
| GET | `/auth/me` | Return current user and active workspace |
| POST | `/auth/password/request` | Start password reset flow |
| POST | `/auth/password/reset` | Complete password reset |
| GET | `/workspaces` | List accessible workspaces |
| POST | `/workspaces` | Create a workspace |
| GET/PATCH | `/workspaces/{id}` | Read/update workspace settings |
| GET/POST/PATCH/DELETE | `/workspaces/{id}/members` | Manage memberships |
| POST/DELETE | `/workspaces/{id}/invitations` | Invite or revoke an invitation |
| GET/PATCH | `/workspaces/{id}/branding` | Manage logo, colors, and company details |
| GET | `/credits` | Show plan, balance, reservations, and usage |

## Discovery and leads

| Method | Path | Purpose |
|---|---|---|
| GET | `/leads` | Paginated, filterable lead list |
| GET | `/leads/map` | Minimal viewport pin data |
| GET | `/leads/{id}` | Full lead detail and score summary |
| POST | `/discovery/search` | Start category/city/area/radius discovery |
| POST | `/discovery/scan-area` | Start viewport discovery and classification |
| POST | `/imports/csv` | Start a CSV import job |
| GET/POST/PATCH/DELETE | `/saved-searches` | Manage saved filter definitions |
| GET | `/jobs/{id}` | Read job status and progress |
| GET | `/jobs/{id}/events` | Stream job progress using SSE |

`GET /leads/map` accepts `bbox`, `zoom`, and URL-safe filter parameters. Each
pin returns only:

```json
{
  "id": "lead-uuid",
  "latitude": 24.86,
  "longitude": 67.01,
  "status": "NO_WEBSITE",
  "severity": "CRITICAL",
  "opportunityScore": 88,
  "leadValueTier": "HIGH"
}
```

`GET /leads/{id}` adds business name/category/address/phone/rating/reviews,
website classification, `severityReasons`, audit category scores, pipeline
stage, assignment, and permitted actions.

Filters include website status, severity, category, city/area, rating, review
count, audit-score range, pipeline stage, and assigned member. Filter state is
also represented in the frontend URL.

Discovery uses an OSM provider abstraction. The MVP provider supports bounded
Overpass category/name queries and Nominatim geocoding with a descriptive
User-Agent. `POST /imports/csv` accepts a CSV with `name`, `latitude`, and
`longitude`; `category`, `address`, `phone`, `website`, `rating`, and
`review_count` are optional. Provider failures return an explicit
`provider_unavailable` error rather than an empty successful result.

Website classification follows normalized HTTP(S) URLs, detects social-only
hosts, resolves addresses before connecting, blocks private/internal address
ranges, follows a small bounded redirect chain, and marks timeouts, HTTP
errors, parked pages, and DNS failures as `DEAD_SITE`.

## Audit endpoints

`POST /leads/{id}/audit` fetches the public website through the SSRF-safe
crawler and evaluates the registered rule set. The current Phase 4 rules cover
HTTP status, HTTPS, title, meta description, H1 structure, mobile viewport,
and visible contact/conversion signals. The response includes the overall score,
category scores, issue count, severity, and explainable severity reasons.
The bounded MVP execution completes within the request; queue-backed progress
streaming remains part of the platform hardening phase.

`GET /audits/{id}` returns each issue with its rule ID, category, severity,
confidence, affected URL, evidence, plain-language explanation, and fix
recommendation. Unavailable measurements are reported explicitly. PageSpeed
metrics remain an optional provider and are not fabricated when unconfigured.

## Phase 5 pitch behavior

`POST /leads/{id}/pitches` creates a deterministic, fact-grounded draft from
the lead and latest audit. It returns English and Urdu outreach variants,
three phased recommendations, scope, timeline, and explicitly unpriced terms.
No LLM or invented business facts are used. Workspace services and packages
are managed through the service catalog endpoints and can be selected by ID
when a pitch is created; selected services return a transparent PKR estimate.

`POST /pitches/{id}/share` returns an opaque token; only its hash is stored.
`GET /share/{token}` exposes the minimum public projection, records a view,
and rejects revoked or expired links. Private workspace notes and internal
pricing are not included in the public response.

## Audits and scoring

| Method | Path | Purpose |
|---|---|---|
| POST | `/leads/{id}/audit` | Start or refresh an audit |
| GET | `/leads/{id}/audits` | List audit versions |
| GET | `/audits/{id}` | Read audit summary and progress |
| GET | `/audits/{id}/issues` | Filter issues by category/severity |
| GET/PATCH | `/score-profiles` | Read or manage workspace score weights |

Audit responses include category scores, overall score, measured/unavailable
metrics, rule versions, evidence, affected URLs, plain-language explanations,
fix guidance, and confidence. No metric is fabricated when PageSpeed or a
crawl capability is unavailable.

## Pitches, services, and public pages

| Method | Path | Purpose |
|---|---|---|
| POST | `/leads/{id}/pitches` | Generate a fact-grounded draft |
| GET/PATCH | `/pitches/{id}` | Read or edit a pitch |
| POST | `/pitches/{id}/pdf` | Download a proposal PDF |
| POST | `/pitches/{id}/share` | Create or rotate a public share link |
| DELETE | `/pitches/{id}/share/{shareId}` | Revoke a public link |
| GET | `/share/{token}` | Read the scoped public pitch projection |
| GET/POST/PATCH/DELETE | `/service-catalog` | Manage workspace services |
| GET/POST/PATCH/DELETE | `/service-packages` | Manage priced packages |

Pitch outputs include phased recommendations, selected services, labelled
estimates, English and Urdu outreach variants, a call script, scope,
timeline, price, terms, branding, and generation version. Public projections
exclude private notes and internal-only fields.

## Prototypes

| Method | Path | Purpose |
|---|---|---|
| GET | `/prototype-templates` | List available industry templates |
| POST | `/leads/{id}/prototypes` | Start a data-bound prototype |
| GET/PATCH | `/prototypes/{id}` | Read or edit a draft |
| GET | `/prototypes/{id}/preview` | Preview the selected version |
| POST | `/prototypes/{id}/export` | Generate and download an HTML/React ZIP immediately |
| GET | `/prototype-exports/{id}` | Read export status |
| GET | `/prototype-exports/{id}/download` | Download a completed artifact |

Phase 6 templates are versioned server-side and bind only approved lead facts
into the prototype. Editor updates are limited to known sections, bounded
plain text, and validated six-digit theme colors; generated HTML escapes all
content and does not execute user-supplied markup or remote scripts. The MVP
export endpoint returns a clean ZIP immediately for `html` or `react`; queued
export tracking remains compatible with the later worker hardening phase. The
export metadata and download routes are workspace-scoped; the MVP regenerates
the ZIP from the current sanitized prototype content.

Prototype generation uses approved lead facts, selected industry template,
editable copy, original/placeholder imagery, and sanitized user input. The
downloaded ZIP is a clean project, not a locked runtime dependency.

## Pipeline, teams, and reporting

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/pipeline/cards` | List/create pipeline cards |
| PATCH | `/pipeline/cards/{id}` | Edit stage, notes, and metadata |
| POST | `/pipeline/cards/{id}/move` | Move through New, Contacted, Pitched, Negotiating, Won/Lost |
| GET/POST | `/pipeline/cards/{id}/activities` | Read/create activity history |
| GET/POST/PATCH/DELETE | `/follow-ups` | Manage reminders |
| POST/DELETE | `/leads/{id}/assignments` | Assign or unassign members |
| GET | `/reports/overview` | Funnel, cities, categories, credits |
| GET | `/reports/members` | Per-member activity and outcomes |

Every stage change creates an immutable activity and an outbox event.

## Developer API, exports, and webhooks

The versioned developer API mirrors safe lead, audit, pitch, prototype, and
pipeline read/write operations under `/api/v1`. API keys have scopes such as
`leads:read`, `audits:read`, `pitches:write`, and `webhooks:manage`.

| Method | Path | Purpose |
|---|---|---|
| POST/DELETE | `/api-keys` | Create or revoke a scoped key |
| GET | `/api-keys` | List key metadata, never secrets |
| GET | `/exports/leads.csv` | Export permitted leads |
| GET | `/exports/audits.json` | Export permitted audits |
| GET/POST/PATCH/DELETE | `/webhooks` | Manage signed webhook endpoints |
| POST | `/webhooks/{id}/test` | Queue a test delivery |
| GET | `/webhooks/{id}/deliveries` | Inspect delivery status |

The Phase 7 MVP stores scoped API keys and webhook subscriptions and exposes
workspace-scoped CSV/JSON exports. Keys and webhook signing secrets are
returned only at creation. Delivery retries and persistent delivery history
remain a follow-up worker enhancement; the API does not claim delivery success
until that worker is enabled.

Webhook event names:

- `lead.discovered`
- `website.classified`
- `audit.completed`
- `pitch.viewed`
- `pipeline.stage_changed`
- `prototype.export_completed`

Deliveries are signed, retried with backoff, idempotent, and recorded.

## Compliance and health

| Method | Path | Purpose |
|---|---|---|
| POST | `/opt-out-requests` | Request listing removal or suppression |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Database/Redis/provider readiness |
| GET | `/openapi.json` | Generated API specification |

Opt-out requests are auditable and prevent future discovery or outreach for
the matching business where identity can be established.

## Authorization summary

- Unauthenticated users may access only registration/login and public share
  links that have a valid, unexpired token.
- All workspace resources require membership and an active workspace context.
- Owners manage membership, plan settings, branding, and all workspace data.
- Managers manage team operations, assignments, catalogs, and reports.
- Sales members manage permitted leads, pitches, and pipeline activity.
- Developers manage prototypes and approved developer API surfaces.
- API keys cannot exceed the creator's workspace permissions.

## Versioning and idempotency

Long-running POST requests accept an idempotency key. Repeating a key returns
the existing job or artifact rather than double-charging credits. API versions
are additive where possible; breaking changes require a new `/api/vN` prefix.
