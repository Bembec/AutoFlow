# Roadmap status

Where the codebase stands against the roadmap's build order and Phase 1 (MVP) requirements.

## Build order

| Stage | Status | Versions |
| --- | --- | --- |
| Clickable prototype | ✔ Superseded by the real web app | V14 |
| Core foundation: accounts, isolated workspaces, database, reliable engine | ✔ | V9, V10 |
| AI builder: plain words → workflow | ✔ | V11 |
| First integrations + webhooks | ✔ Airtable, SMTP/Gmail, REST APIs, Google Sheets (OAuth), Shopify webhooks | V12 |
| AI steps and approvals | ✔ | V8, V13 |
| Dashboard and billing | ✔ | V14, V15 |
| Operational readiness | ✔ | V16 |

## MVP must-haves

| Requirement | Status |
| --- | --- |
| AI workflow builder (chat + canvas) | ✔ Chat-style drafting with questions, canvas, and a visual step editor |
| Dependable engine: retries, timeouts, no duplicate actions | ✔ |
| Three working automations for the first niche | ✔ E-commerce (chosen): order → invoice, abandoned-cart follow-up, review replies (V19) |
| 3–5 reliable integrations + webhooks | ✔ |
| Secure accounts, team members, tenant isolation | ✔ |
| Draft, test and publish modes | ✔ Plus versions and rollback |
| Run history, error handling, approval steps | ✔ |
| Usable dashboard and basic billing | ✔ |

## Commercial readiness requirements

| Requirement | Status |
| --- | --- |
| Multi-tenant architecture | ✔ |
| Reliable execution (idempotency, timeouts, recovery, cancel, replay, modes) | ✔ |
| Integration security (OAuth refresh, encrypted isolated credentials, webhook signatures, revoked access) | ✔ Per-integration rate-limit handling is basic (429 is retried) |
| AI safety and control (approvals, prompt injection, limited tools, emergency stop, mandatory policies, limits) | ✔ |
| Operational readiness (staging/production, tests, deploy/rollback, monitoring, incidents) | ✔ Uptime monitor and log platform still to be connected |
| Billing and usage protection | ✔ AI-credit packs not yet |
| Data ownership (export, deletion, backups) | ✔ Restore testing is a monthly runbook task |

## Next, in order

1. **Decide the remaining open questions**: launch country, brand name, build vs. buy integrations, funding route. (Niche decided: e-commerce.)
2. ~~Three niche automations~~: done in V19 (they use Shopify webhooks; a Shopify Admin API connector can come later, e.g. to post review replies or tag orders).
3. ~~Visual step editing~~: done in V18 (form editor with drag-to-reorder, next to the canvas).
4. ~~Background execution queue and `delay` steps~~: done in V17.
5. ~~Email/document triggers~~: done in V20 (IMAP inbox watch, document uploads, AI OCR).
6. **Choose and set up a cloud host** (AWS/GCP), managed PostgreSQL, uptime monitoring, error tracking and a status page.
7. **Website and legal**: terms, privacy policy, DPA, sub-processor list (see the full roadmap).
