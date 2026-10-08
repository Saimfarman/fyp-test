# LeadPitch product scope

## Product goal

Help freelancers, independent developers, and small software houses find local
business opportunities quickly, understand why a business may need help, and
produce a credible next action without inventing facts.

The initial market configuration is Pakistan, with Karachi, Lahore, Islamabad,
Rawalpindi, Faisalabad, Peshawar, and Multan as default cities. The UI is in
English; generated pitches, outreach copy, and prototype copy support English and
Urdu. Prices default to PKR and remain editable per user or workspace.

## MVP scope

### Freelancer

- OSM discovery by category, city/area, map viewport, or radius.
- Website classification: no website, social-only, dead site, live website.
- Bounded website audit with explainable issues and scores.
- Severity, opportunity score, reasons, filters, sorting, and CSV/JSON export.
- Saved leads, simple pipeline, bilingual WhatsApp/email/call copy.
- Branded shareable pitch/audit page and proposal PDF.
- Internal usage credits and a responsive installable PWA.

### Independent developer

- Lead and audit API foundation with OpenAPI documentation.
- Industry-template prototype generation.
- Unique preview URL, device switcher, basic text/color/logo editing.
- ZIP export of clean static files suitable for continued development.
- CSV/JSON export and provider interfaces for future integrations.

### Software house or small agency

- Workspaces and invitations.
- Owner, manager, sales/BD, and developer roles.
- Shared pipeline, lead assignment, notes, follow-ups, and activity history.
- Workspace branding and editable service catalog/package pricing.
- Professional proposal PDF generation.
- Per-member activity/reporting foundations.

## Later scope

- Google Places/Google Maps adapter when an appropriate subscription and
  compliance review are available.
- Hosted or local LLM providers, image providers, and richer copy controls.
- Billing checkout, subscriptions, invoices, and payment recovery.
- OAuth providers and enterprise SSO.
- Custom domains for public share links.
- Advanced bulk assignment, automation, collaboration, and analytics.
- Mature framework starter exports, richer block editing, and third-party
  integrations.
- Native iOS/Android wrappers. A later wrapper would reuse the API and add
  platform builds, push/deep-link handling, device permissions, and store
  compliance; it is not part of the web MVP.

## Explicit non-goals

- Scraping Google Maps or Google business pages.
- Automated WhatsApp/email sending in the MVP.
- Claiming an OSM field is false merely because it is absent.
- Reusing Google-hosted or copyrighted business imagery.
- A locked prototype builder that prevents developers from owning exported code.
- Native mobile applications.

## Acceptance targets

- Users can distinguish website status and severity without relying on color.
- Pin labels do not overlap at any zoom level.
- Map pan/zoom remains usable with 5,000+ leads.
- First meaningful map experience targets about two seconds on a mid-range phone.
- Pin to generated pitch/prototype requires no more than two primary actions.
- Layout works at approximately 360, 768, 1024, 1440, and 2560 px widths.
- Latest two versions of Chrome, Edge, Firefox, and Safari are supported on
  desktop and mobile.
- Hover interactions have touch and keyboard equivalents.
- The PWA shell loads offline and presents a clear offline state for live work.

## Responsible outreach and data policy

The product should encourage human-reviewed, relevant outreach and show
responsible-use guidance. It must support an opt-out/removal request, keep
provider attribution visible, record data refresh timestamps, and avoid
retaining more third-party data than the provider's terms permit. No generated
copy may state an unverified fact as certain; estimates must be labelled.

