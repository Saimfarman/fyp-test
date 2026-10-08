# ROLE
You are a senior full-stack engineer and technical architect working inside my codebase. Work step by step, ask before assuming anything important, and never skip the approval gates in "WORKING RULES".

# CONFIGURABLE VARIABLES (edit to reuse this prompt for another market)
- PROJECT_NAME: LeadPitch (working title)
- TARGET_COUNTRY: Pakistan
- DEFAULT_CITIES: Karachi, Lahore, Islamabad, Rawalpindi, Faisalabad, Peshawar, Multan
- CURRENCY: PKR
- LANGUAGES: English UI; English + Urdu for generated pitches, outreach copy, and prototypes
- BACKEND: Python + Quart (ASGI)
- FRONTEND: my choice is delegated to you; justify it (recommended: Next.js + TypeScript + Tailwind + GSAP ScrollTrigger + Lenis)
- MAP: Google Maps JavaScript API (vector map + AdvancedMarkerElement), behind a pluggable map-adapter interface

# PRODUCT SUMMARY
A platform that helps people who sell digital services find local businesses in TARGET_COUNTRY that lack a website or have a weak one, then pitch them website, SEO, and marketing services. It has three parts:
1. DISCOVER: find businesses on Google Maps and detect whether each has a real website, and how severe their situation is.
2. DIAGNOSE & PITCH: audit existing websites, score how much each business needs help, and generate a ready-to-send pitch with SEO and marketing recommendations.
3. PROTOTYPE: generate a website prototype for a business so the seller can show it as part of the pitch.

# PLATFORM & DEVICE SUPPORT (IMPORTANT)
- This is a WEB application, not a native mobile app. It must run in any modern browser on any device (Windows, macOS, Linux, Android, iOS) with nothing to install.
- Treat desktop, tablet, and phone as equally important. Sellers do heavy work (lead lists, pipeline, proposals, prototype editing) on desktop, and quick work (checking leads, sending WhatsApp pitches) on phones. Design layouts for each, not one scaled down from the other.
- Supported browsers: latest two versions of Chrome, Edge, Firefox, and Safari (desktop and mobile). Test breakpoints at roughly 360, 768, 1024, and 1440+ px.
- Make it an installable PWA (manifest, icons, service worker for app-shell caching, graceful offline message). Do NOT build native iOS/Android apps. A Capacitor/native wrapper is a "later" idea only.
- The backend runs in Docker on any host (laptop, VPS, cloud). Users only need a browser and a URL.
- Support touch, mouse, and keyboard input everywhere (hover behaviors need touch equivalents).

# TARGET AUDIENCE (design every feature for these users)
1. Solo freelancers (web developers, designers, SEO and social media marketers): need speed and low cost. Find leads, pitch in minutes, send via WhatsApp, track a simple pipeline. Need a free/cheap tier with usage credits.
2. Independent software developers: want prototypes they can keep building. Prototype export must be a clean, well-structured code project (not a locked builder), plus API access, CSV/JSON export, and webhooks.
3. Software houses and small agencies: need teams. Multi-user workspaces, roles (owner, manager, sales/BD, developer), lead assignment by city/category, a shared pipeline, per-member reporting, white-label branding (logo, colors, custom domain for share links), a service catalog with package pricing, and professional proposal PDFs.
All three buy from small local business owners, so generated pitches must be simple, credible, plain-language, and in the owner's language (English/Urdu).

# REFERENCE ANALYSIS (borrow ideas; never copy branding, code, or content)
- PitchGen (pitchgen.io): URL -> audit across 8 categories -> prioritized recommendations in 4 phases -> one-click pitch deck, white-label shareable audit. Model for the pitch flow.
- SEOmator (seomator.com): crawler with ~250 rules across ~20 categories; each issue lists the affected page and a fix tip; white-label PDF reports; task list of fixes; Google Business Profile audit. Model for the website-corrections audit.
- Insites (insites.io): low-code platform with CMS, CRM, sales pipelines, staging/production instances. Inspiration only for the pipeline and prototype preview environments.
- None of these discover businesses via maps. The map-based discovery with severity is this project's unique feature.
If you can browse, briefly verify these notes. If not, trust them.

# MAP UI REFERENCE (a rough mockup may be attached; if you cannot see it, use this description)
A mobile map app on a Google basemap. Blue pins marked "W" are businesses that own a website; orange pins marked "X" have none. Tapping a pin opens a bottom card with name, rating, address, and either "WEBSITE: OWNED" with a link or "NO WEBSITE". Its weaknesses, which my version must fix:
- Only two states, no severity.
- Overlapping pin labels and duplicated zoom controls.
- Status relies mostly on color.
- No pitch, prototype, or save actions.
- No filters, search-this-area, or lead list.
- Mobile only.
My frontend must be clearly more polished, informative, and actionable than this reference.
Note: the mockup shows phone screens only because it is a rough sketch. The product is a responsive web app, and the desktop layout (three-pane) is the primary experience for heavy work.

# CORE MODULES

## 1. Business Discovery
- Input: category/keyword + city/area (from DEFAULT_CITIES), map viewport, or radius.
- Data source: Google Places API (New), Text Search / Nearby Search with field masks (name, address, phone, rating, review count, website URI, business status, location, place_id). Do NOT scrape Google Maps.
- Pluggable data-source layer with adapters for Google Places, OpenStreetMap (Overpass, as a fallback), and CSV import.
- Handle pagination, quotas, retries with backoff, and a configurable monthly budget cap with a visible usage counter. Tie usage to a per-user/workspace credits system.
- Respect the provider's terms on caching/storage: store place_id long-term, refresh other fields periodically, and document the current terms in the README.

## 2. Website Detection & Classification
Classify every business as:
- NO_WEBSITE
- SOCIAL_ONLY (Facebook, Instagram, WhatsApp link, linktr.ee, etc.)
- DEAD_SITE (DNS failure, timeout, 4xx/5xx, parked domain)
- HAS_WEBSITE (live and reachable)
Normalize URLs, follow redirects, and detect parked or placeholder pages.

## 3. Website Audit (for HAS_WEBSITE)
Async crawl of the homepage plus a few key pages (obey robots.txt, rate limits, clear User-Agent). Check at least:
- Technical: HTTPS/certificate, redirects, status codes, broken links, sitemap.xml, robots.txt, canonical tags
- On-page: title, meta description, H1/H2 structure, image alt text, LocalBusiness structured data, Open Graph tags
- Performance: Core Web Vitals and Lighthouse metrics via the PageSpeed Insights API (mobile + desktop)
- Mobile: viewport tag, responsive layout, tap targets
- Local SEO: NAP consistency with the Maps listing, embedded map, Google Business Profile completeness (hours, photos, reviews)
- Conversion/trust: visible contact info, WhatsApp/click-to-call, contact form, social links, analytics/pixel
Each issue includes category, severity, affected URL, plain-language explanation, and a how-to-fix recommendation. Give each category a 0-100 score plus an overall score. Make rules plugin-based so new checks are easy to add.

## 4. Severity & Lead Scoring (configurable; always show reasons)
Severity = how badly a business needs website/SEO/marketing help:
- CRITICAL (red): NO_WEBSITE, DEAD_SITE, or audit score < 30
- HIGH (orange): SOCIAL_ONLY, or audit score 30-49
- MEDIUM (amber): audit score 50-69
- LOW (green): audit score >= 70
- UNSCANNED (gray): not audited yet
Within a tier, rank by lead value (rating x review volume). Provide an explainable 0-100 opportunity score with configurable weights. The backend returns `status`, `severity`, `severity_reasons[]`, `audit_score`, and `lead_value_tier` for every lead. Filters, sorting, and CSV/JSON export are required.

## 5. Map Experience (the signature screen)
Pins:
- Color = severity. Glyph inside the pin = website status (X = none, broken-link = dead, social icon = social-only, globe = has website). Audit score shows as a small badge on pins with websites.
- Never rely on color alone: distinct glyphs, text severity labels in cards and legend, color-blind-safe palette, and legibility in grayscale.
- Pin size reflects lead value (3 tiers). High-value CRITICAL leads get a subtle pulse.
- No permanent name labels on pins. Show names on hover/selection or at high zoom, with label-collision handling so text never overlaps.
- A legend that doubles as a quick filter.
Behavior:
- Google Maps JavaScript API with AdvancedMarkerElement and vector maps. Keep Google attribution visible. Use the pluggable map adapter (MapLibre only for non-Google data).
- Clustering shows count and the worst severity inside. Viewport-based loading from a lightweight endpoint (bbox, zoom, filters). Smooth (about 60fps) with 5,000+ leads.
- Controls: "Search this area", "Scan this area" (starts a discovery job for the viewport), map/satellite/dark styles, my location, opportunity heatmap toggle, optional draw-an-area selection.
- Pins update live while jobs run (SSE/WebSocket): gray pins turn their final color as audits finish, with a progress indicator.
Layout:
- Desktop: three panes with a filter + virtualized lead list on the left (synced with the map), the map in the center, and a detail drawer on the right. Hover and click link list items and pins both ways.
- Mobile: full-screen map, filter chips on top, and a draggable bottom sheet with three snap points (peek, half, full).
- Filters: website status, severity, category, city/area, rating, review count, audit-score range, pipeline stage, assigned team member. Filters sync to the URL so views are shareable.
Lead detail drawer/card: name, category, rating, address, phone, status chip, severity chip with top 3 reasons, website link, mini score bars (Technical, On-page, Performance, Mobile, Local SEO), and actions: Generate Pitch, Create Prototype, Save to Pipeline, Assign (teams), Open in Google Maps, WhatsApp/Call.

## 6. Pitch Generator
For each lead, generate:
- A shareable white-label pitch/audit page (public link with unguessable token and optional expiry) plus PDF export, using the seller's or workspace's branding.
- Prioritized recommendations in phases (quick wins, website build/fix, SEO, marketing/social/ads), built from a service catalog with package pricing in CURRENCY (editable per user or workspace).
- Outreach copy for WhatsApp, email, and a call script in English and Urdu.
- Proposal PDF (scope, timeline, price, terms) for software houses.
- LLM text goes through a pluggable provider interface (no hard-coded vendor) with a template fallback when no key is set. Never invent facts: use only collected data, and label any estimate as an estimate.

## 7. Website Prototype Generator
- Input: lead data (name, category, address, phone, hours, rating, selected reviews) + chosen industry template and style.
- Output: responsive prototype (home, about, services, gallery, contact, map) from a library of industry templates (restaurant, clinic, salon, retail, services, etc.), with LLM-assisted copy (template fallback) and stock/placeholder imagery. Do NOT reuse Google-hosted photos or copyrighted material.
- Preview at a unique URL with a device switcher (desktop/tablet/mobile) and basic editing (text, colors, logo).
- Export: ZIP of clean static files, plus an optional framework starter project (e.g. Next.js or plain HTML/Tailwind) that developers can continue from.
- Packages include SEO and marketing add-ons: meta tags, LocalBusiness schema, sitemap, Google Business Profile optimization checklist, social content ideas, and a review-collection plan.

## 8. Pipeline, Teams & Dashboard
- Stages: New -> Contacted -> Pitched -> Negotiating -> Won/Lost, with notes, follow-up reminders, and activity history.
- Workspaces with roles (owner, manager, sales, developer), invitations, lead assignment (manual and by city/category), shared pipeline, and per-member performance reports.
- White-label settings: logo, colors, company details, optional custom domain for share links.
- Dashboard: leads found, funnel, top categories/cities, credits and API budget usage.
- Auth: email/password + OAuth, JWT or session-based, RBAC, strict per-workspace data isolation.
- Plans/credits: free, pro, and team tiers enforced by usage credits for discovery, audits, and prototypes (billing integration is out of MVP scope, but design for it).

## 9. Developer Features
- Public REST API with API keys and rate limits, OpenAPI docs, and webhooks (lead discovered, audit complete, pitch viewed, stage changed).
- CSV/JSON export of leads and audits.

# TECHNICAL REQUIREMENTS

## Backend (Quart)
- Quart on Hypercorn (or Uvicorn), fully async (httpx/aiohttp, asyncpg).
- Postgres (SQLAlchemy 2.x async + Alembic), Redis for cache, rate limiting, and the job queue.
- Long-running work (discovery, crawls, audits, prototype builds, PDF generation) runs in background workers (arq, Dramatiq, or Celery; choose one and justify). Endpoints return job IDs; progress is streamed via SSE/WebSocket.
- Validation (quart-schema or Pydantic), consistent error format, pagination, structured logging, health/readiness endpoints.
- Security: SSRF protection on any user-supplied URL (block private/internal IPs), rate limiting, CORS, secrets only via environment variables, audit logs for team actions.
- Map endpoints: GET /leads/map?bbox=&zoom=&filters (minimal pin data: id, lat, lng, status, severity, score, value_tier), GET /leads/{id} (full detail), POST /discovery/scan-area (viewport job + progress stream).

## Frontend
- Fast, responsive, web-first and device-agnostic (desktop, tablet, phone equally supported), with smooth scroll-driven animations on landing/marketing pages (GSAP ScrollTrigger + Lenis or equivalent). In-app motion stays restrained (pin drop-in, spring drawer, count-up stats) and must never hurt map performance. Honor prefers-reduced-motion.
- Modern, high-contrast design system (tokens, light/dark theme), skeleton loaders, helpful empty states.
- Accessibility: WCAG AA contrast, keyboard-accessible pins/list/drawer, ARIA labels that state website status and severity in text.
- Lighthouse >= 90 (performance and accessibility) on the landing page. Code splitting, optimized images, lazy loading.
- Screens: landing, map + discovery, lead detail/audit report, pitch builder, prototype studio, pipeline board, team/workspace settings, service catalog, dashboard, API/webhook settings.

## Docker & Deployment
- Multi-stage Dockerfiles, non-root users, small images, healthchecks.
- docker-compose with: reverse proxy (Nginx or Caddy), backend (multiple workers), job worker, frontend, Postgres, Redis. Separate dev and prod configs, persistent volumes, `.env.example`.
- Stateless backend so it scales horizontally behind the proxy; include short scaling notes.
- One-command start (`docker compose up`), Makefile/scripts for common tasks, CI (lint, tests, build), and a README with setup, architecture diagram, and API overview.

## Quality
- Tests for classification, severity/scoring, audit rules, and API; type hints; linting/formatting configured.
- Modular, plugin-style design for audit rules, data sources, prototype templates, and LLM providers.

# ACCEPTANCE CRITERIA FOR THE MAP SCREEN
1. A user can tell at a glance, without reading, which businesses lack a website and how severe each case is.
2. Status and severity remain understandable in grayscale.
3. No overlapping labels at any zoom level.
4. Pan/zoom stays smooth with 5,000+ leads; first meaningful paint under about 2 seconds on a mid-range phone.
5. From pin click to a generated pitch or prototype takes at most 2 clicks.
6. The same screen works well on desktop, tablet, and mobile.
7. The full app works in the latest Chrome, Edge, Firefox, and Safari on desktop and mobile, with no layout breakage between 360px and 2560px widths.
8. All hover-only interactions have a touch/keyboard equivalent.
9. The app can be installed as a PWA and still loads its shell without a connection.

# LEGAL & ETHICAL GUARDRAILS
- Use official APIs only; no scraping of Google properties.
- Respect robots.txt and rate limits when crawling business sites.
- Use public listing data only. Provide an opt-out/removal mechanism and guidance for responsible outreach (no spam; follow local rules and platform policies, including WhatsApp's).

# WORKING RULES (IMPORTANT)
1. Do NOT write application code yet. Start with PHASE 1 only.
2. If anything critical is unclear (API budget, hosting target, LLM provider, billing needs), ask at most 5 concise questions first and list default assumptions for the rest.
3. Work in phases and STOP for my approval after each:
   - PHASE 1: Architecture & plan
   - PHASE 2: Scaffold + Docker + DB schema + auth + workspaces/roles
   - PHASE 3: Discovery + website detection + map screen (core)
   - PHASE 4: Audit engine + severity/lead scoring
   - PHASE 5: Pitch generator + PDF/share links + service catalog
   - PHASE 6: Prototype generator + preview/export
   - PHASE 7: Pipeline/teams reporting, developer API/webhooks, map polish, animations, performance, PWA, tests, docs
4. MVP-first: mark every feature as MVP or later.
5. After each phase, summarize what was built, how to run and test it, and what's next.

# PHASE 1 DELIVERABLES (do this now)
1. Short comparison of the three reference sites and what we adopt from each.
2. Final scope: MVP vs later, per audience (freelancer, developer, software house).
3. System architecture (components, data flow, Mermaid/text diagram) and justification of frontend, queue, and LLM choices.
4. Database schema (including workspaces, roles, credits).
5. API endpoint list grouped by module.
6. Audit rule catalog, severity rules with default thresholds, and the lead-scoring formula with default weights.
7. Wireframe-level description of the map screen, lead drawer, and pin/legend design spec.
8. Repo folder structure (monorepo: backend, frontend, docker, docs).
9. Docker/compose design and scaling notes.
10. Risks (API costs, ToS, crawl limits, data freshness, outreach compliance) and mitigations.
11. A milestone timeline suited to a final-year project, plus the open questions from rule 2.
12. Confirmation of the web/PWA platform decision, the browser support matrix, responsive breakpoints, and a note on what would be needed to add a native app later.