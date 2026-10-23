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

1. **Decide the remaining open questions**: launch country, brand name, build vs. buy integrations, funding route, and (added October 2026) positioning, Shopify route, Gmail access, Free plan. (Niche decided: e-commerce.)
2. ~~Three niche automations~~: done in V19 (they use Shopify webhooks; a Shopify Admin API connector can come later, e.g. to post review replies or tag orders).
3. ~~Visual step editing~~: done in V18 (form editor with drag-to-reorder, next to the canvas).
4. ~~Background execution queue and `delay` steps~~: done in V17.
5. ~~Email/document triggers~~: done in V20 (IMAP inbox watch, document uploads, AI OCR).
6. **Choose and set up a cloud host** (AWS/GCP), managed PostgreSQL, uptime monitoring, error tracking and a status page.
7. **Website and legal**: terms, privacy policy, DPA, sub-processor list (see the full roadmap).
8. ~~Design system and in-app polish~~: done in V29 (swappable brand theme, icons, plain-language run view and errors, loading skeletons, accessibility pass).
9. ~~Guided onboarding~~: done in V30 (Get started page with platform-based template picks, live checklist on the dashboard).
10. ~~Public website pages~~: done in V31 (home with "type a task" demo, templates, integrations, pricing, security). The site is translated into all five languages since V46. Legal pages and customer stories wait on brand, legal and launch decisions.
11. ~~Time/cost-saved dashboard and process discovery~~: done in V32 (Insights page, explainable suggestions).
12. ~~Smarter workflow logic~~: done in V36 behind the `smarter_logic` flag (comparisons, AND/OR groups, for-each loops). AI decision steps already work as AI classify + a condition.
13. ☑ **Template library**: 36 tested templates since V47 (32 for e-commerce, plus 3 assistant roles and 1 general), beyond Phase 2's 25+. More will follow from design-partner requests. **AI assistants** for set roles come at the end of Phase 2 (roadmap v2).

## Phase 1 additions from the October 2026 review

The roadmap was updated to version 2.0 on 2026-10-23. Legend: ☑ built, ◐ partly built, ☐ to do.

| Item | Status | Notes |
| --- | --- | --- |
| Platform verifications (Google CASA, Shopify review, WhatsApp, Microsoft) | ☐ | Depend on the Gmail-access and Shopify-route decisions |
| Sending limits | ☑ | Daily email, run and AI limits per workspace (V13) |
| New-account restrictions, outbound content checks, abuse reports | ☑ | V33 |
| Email from the customer's own mailbox | ☑ | Each workspace's own SMTP connection |
| Acceptable-use policy enforced in product | ◐ | V33: staff suspension, phishing block; policy text still needs legal |
| AI-provider data terms on trust page | ☐ | Needs provider choice and legal review |
| Pinned models + 200-request test set as release gate | ◐ | V35: 60 synthetic cases, first-time pass rate ≥ 80% gate in the runner; real customer requests (to 200+) come from pilots |
| AI cost meter and hard cap | ☑ | V33: monthly AI budget per plan (estimated USD); tune with real bills |
| Label AI-generated messages | ☐ | Scope to check with counsel |
| Untrusted input handling | ☑ | Prompt-injection guard, limited tools, review queue |
| Definition of done, item status with owners | ◐ | V35: docs/engineering/definition-of-done.md + PR template; owners once "who builds it" is decided |
| Test strategy | ◐ | 242 tests incl. duplicate soak, tenant isolation, billing; connector contract tests against sandboxes to do |
| Staging, demo workspace, feature flags | ◐ | V35: seeded demo workspace and feature flags done; a running staging environment needs the hosting decision |
| Recovery targets | ◐ | Runbook exists; targets set once hosting is chosen |
| Compensation (undo) | ☑ | V34: void invoice (app and workflow step), confirm-done for uncertain steps |
| Test mode with sample data | ☑ | |
| Run timeline with cost | ☑ | V29 timeline + V33 AI calls and estimated cost per run |
| Connection health and one-click reconnect | ◐ | V34: read-only checks, alerts on breakage, one-click reconnect; rate-limit tracking to do |
| WCAG 2.2 AA and plain-language errors | ◐ | V29 pass; formal audit to do |
| Phase 3: workflow evaluations in production (sampling + review queue) | ☑ | V45: deterministic sampling of live AI results (0-20%, default 5%), Good/Not right review with notes, 30-day and per-step quality rates, weekly trend |
| Phase 3: expose workflows as an MCP server | ☑ | V44 behind `mcp_server`: workspace API keys, opt-in per workflow, run/list/get tools, approvals and limits apply, idempotency key, rate limit; real-client check in deferred checks |
| Phase 2 (end): AI agents for set roles | ☑ | V42: `ai_agent` + approval-gated `agent_execute`; V43: Assistants page with 3 ready-made roles (support inbox, order watcher, refund helper), behind `ai_assistants`. Real-AI quality check in deferred checks |
| Phase 2: AI help assistant limited to documentation | ☑ | V40: answers only from the help articles, shows sources, falls back to excerpts without AI, free for customers (rate limited) |
| Phase 2: MCP client support | ☑ | V39 behind the `mcp_tools` flag: MCP server connections with an allowed-tools list, read-only `mcp_read`, approval-gated `mcp_call_tool`, health check; a real-server test is listed in deferred checks |
| Phase 2: workflow versioning with diff and rollback | ☑ | V38: compare any two versions; "what changes when you publish"; publish audit records the changes |
| Gate evidence: zero duplicates in 1,000 test runs | ☑ | V34: 1,000 orders / 1,167 runs, 0 duplicates (docs/evidence/duplicate-soak.md, SQLite); repeat on PostgreSQL in staging |
