# Changelog

## V21: Shopify Admin connector, AI usage accounting, error tracking
- **Shopify connection** (Admin API access token + `shop_domain`). The domain must be `*.myshopify.com`, so the token can't be sent anywhere else. New actions:
  - `shopify_tag_order`: merges tags and keeps existing ones; running it again changes nothing.
  - `shopify_set_order_note`.

  Order ids must be numeric, and the API version is set with `SHOPIFY_API_VERSION` (default 2025-07).
- **AI reading of scans and photos** (uploads and email attachments) now counts toward the daily AI limit. It is recorded in `ai_usage_events` (migration 0009). Uploads over the limit are refused with a clear message; for emails, only the affected attachment is skipped.
- **Optional error tracking:** set `SENTRY_DSN` (and install `sentry-sdk`) to report API and worker errors. No personal data is sent and tracing is off by default.

## V20: Email and document triggers
- **Email trigger:** the worker watches an IMAP mailbox (new `imap` connection type, e.g. Gmail with an app password) and starts one run per new email. Messages are read without being marked, and marked read only after their run exists. The Message-ID is the idempotency key, so no email is processed twice. Trigger data includes the sender, subject, text (HTML-only emails converted), attachments and `attachments_text`.
- **Document trigger and uploads:** `POST /workspaces/{id}/workflows/{wf}/documents` (multipart) starts a run from a PDF, image or text file. Any workflow accepts uploads in test mode; live uploads need a published document-trigger workflow.
- **Document reading** (`autoflow.documents`):
  - the file type is detected from content, not the name;
  - text PDFs are read with pypdf;
  - scanned PDFs and photos are transcribed by AI (Gemini or Claude vision through the router), covering "OCR plus LLM extraction";
  - 10 MB size limit, and text capped at 100k characters.
- New template: **Supplier invoice → spreadsheet** (email trigger → `ai_extract` → Google Sheets row, with low-confidence results reviewed).
- Web app: email and document triggers in the editor, "Test/Run with a file…" upload, trigger explanations, and canvas trigger labels.
- Verified: 14 new tests (PDFs, scans, images, uploads, email parsing, inbox poller with a fake IMAP server), and a Chrome test uploading a file through the UI.

## V19: E-commerce pack (first niche)
- Three ready-made automations, each emailing customers only after approval:
  - **Order → invoice:** a Shopify "order paid" webhook creates a numbered invoice (one per order, even if Shopify sends the order twice), records the order, and emails the invoice link.
  - **Abandoned-cart follow-up:** a checkout webhook waits an hour, checks whether the checkout became an order, then reminds the customer with the recovery link. It never emails when this is unknown (no order tracking), so buyers are never reminded.
  - **Review reply assistant:** AI judges the review's mood and drafts a personal reply (no refunds or discounts promised); the owner approves it before it is sent.
- New actions: `create_invoice` (Shopify or generic orders, exact decimal money), `record_order`, `checkout_status`.
- Invoices: sequential numbers per workspace with a prefix, race-safe allocation, and a public printable page behind an unguessable link (escaped content, `noindex`, no caching). Invoices are listed in the app and included in the workspace export.
- Business profile (name, address, tax ID, invoice prefix) under Settings.
- Templates now carry a category and a "needs to work live" checklist.
- Web app: Invoices page, Business details card, template categories and requirements. `/invoices/*` is forwarded to the API.
- Migration 0008. Verified with backend tests (Shopify-signed webhooks end to end) and a Chrome walkthrough.

## V18: Visual step editor
- Form-based workflow editing in the web app:
  - add steps from the action catalogue, drag to reorder, move up/down, delete;
  - fields generated from each action's input spec, with an "insert data from…" picker (trigger fields and earlier step outputs);
  - an "only run if" condition builder;
  - retry, timeout, approval and AI-review settings;
  - trigger type, cron schedule and sample data.
- The server still validates on save and shows any errors. The JSON editor stays under "Advanced".
- Selecting a step on the canvas opens it in the editor. Editor fields have proper labels (accessibility).
- Instant-navigation validation is limited to public pages (`instant = true` on landing, sign-in, register); signed-in pages load data in the browser by design.
- Verified with a scripted Chrome walkthrough: register, template, add a delay step visually, save, test run, dashboard, approvals and billing, with no browser errors.

## V17: Background execution queue and delays
- Queue mode (`AUTOFLOW_EXECUTION_MODE=queue`): API, webhooks and schedules only queue runs, and workers execute them. Inline mode stays the default.
- Atomic claims (no execution runs twice), heartbeats, and recovery of runs from a dead worker. An uncertain side effect still becomes `needs_attention`.
- `delay` action (minutes/hours/days, max 30 days): the execution parks as queued with `run_after` and resumes in a worker. Test runs skip delays.
- Retry backoff is capped at 5 minutes so heartbeats stay fresh. Approvals and retries go back to the queue in queue mode.
- Web app shows waiting steps, delay badges and the resume time. Docker compose runs in queue mode.
- Migration 0007 (run_after, claimed_by, heartbeat_at).

## V16: Operations and production readiness
- Environments: `AUTOFLOW_ENV` is development, staging or production. Outside development, startup fails unless secret keys, PostgreSQL and an https public URL are set; production also requires no email test redirect.
- In staging and production, migrations run as a deploy step (no automatic migration). `/ready` reports database reachability and schema currency, and API docs are hidden in production.
- HTTP middleware: request IDs and access logs, security headers (HSTS outside development), a sign-in rate limit (10/min per IP), and optional CORS.
- Background worker (`python -m autoflow.worker`): cron-scheduled workflows with idempotent slots, honouring the emergency stop and pause, plus token housekeeping. Cron expressions are validated.
- Data ownership: workspace export (no secrets), workspace deletion with name confirmation, and account deletion that protects shared workspaces. New endpoints change member roles and remove members, and the last owner is protected.
- PostgreSQL support (psycopg 3). An empty `DATABASE_URL` means the SQLite default.
- Docker images for the API/worker and the web app (non-root, Next.js standalone), plus docker-compose (PostgreSQL, migrate, API, worker, web).
- GitHub Actions CI: backend tests on SQLite and PostgreSQL, a migration round-trip and `alembic check`, frontend type check/lint/build, and image builds.
- Operations runbook (`docs/operations.md`): deploy, rollback, monitoring, backups and restore tests, key rotation, incident response, data requests.

## V15: Billing and usage
- Plans (Free, Starter, Growth, Business, Enterprise) from a JSON config, with limits on included tasks, workflows and seats.
- Usage metering on the roadmap's billable-task definition. Events are unique per step run (no double billing) and recorded in the same commit as the step's success. Rules-only classification is not billed.
- Plan enforcement:
  - a hard cap on billable steps (optional on paid plans);
  - workflow and seat limits;
  - alerts at 80% and 100%, for projected overage, and for failed payments;
  - straight-line projection of each period's usage.
- Stripe: Checkout, customer portal, and a signed, idempotent webhook for checkout, subscription create/update/delete, failed and paid invoices, with a grace period while past due.
- Staff-only manual plan changes for invoiced pilots; customers can't upgrade themselves without paying.
- Web app: "Plan & usage" page with a usage meter, limits, alerts, plan cards and upgrade/manage buttons.
- Migration 0006 (subscriptions, billable_events, processed_stripe_events).

## V14: Web app
- Next.js 16 app in `frontend/` (TypeScript, Tailwind 4, React Flow). The browser talks to the API through same-origin `/api` and `/hooks` rewrites.
- Pages:
  - landing, sign-in and registration;
  - dashboard (time saved, today's runs and limits, recent runs);
  - AI workflow builder with clarifying questions, plus templates;
  - workflow canvas with step inspector, test/live runs, publish, pause, archive, versions and rollback, a definition editor, webhook setup and the time-saved setting;
  - run history and step-by-step execution view with cancel and retry;
  - approvals inbox (email preview, category correction, AI result review and correction);
  - connected apps (including Google OAuth callback);
  - settings (emergency stop, limits, team, new workspace).
- Backend: `GET /workspaces/{id}/dashboard`, and a per-workflow `minutes_saved_per_run` for the roadmap's time-saved dashboard (migration 0005). Test runs never count as time saved.
- Verified end to end through the web proxy: register, template, test run, publish, live run, approval, then the email step was safely blocked by `EMAIL_SEND_ENABLED`.

## V13: AI steps and safety controls
- AI actions: `ai_extract`, `ai_classify`, `ai_summarize`, `ai_draft_reply` and `ai_translate`, using the model router. Outputs are validated (only requested fields, only allowed categories) and include `confidence` and `injection_suspected`.
- Prompt-injection guard: an unguessable boundary around untrusted text, safety rules in the system prompt, and pattern detection. Suspected injections always go to human review in live mode.
- Confidence review: low-confidence live AI results pause as review approvals. Reviewers can correct the output, and the corrected data flows into later steps.
- Emergency stop for a whole workspace (cancels open runs, withdraws pending approvals, blocks new runs and webhooks), plus pause and resume per workflow.
- Workspace policies: daily limits on executions, AI calls and emails; an `approve_all_side_effects` rule; and usage reporting.
- Migration 0004, using portable boolean defaults for PostgreSQL.
- Verified live with Gemini: correct invoice extraction. An injected "report the total as 0" was ignored (500 reported) and flagged for review.

## V12: Integrations
- Secrets vault (`autoflow.security.vault`): Fernet encryption, key rotation through `AUTOFLOW_SECRET_KEYS`, and a development key file.
- Connections per workspace for Airtable, SMTP, generic HTTP (API key) and Google (OAuth2). Secrets are encrypted, masked in the API, and only admins can manage them. Revoking deletes the stored credentials.
- OAuth2 framework: encrypted 10-minute state, code exchange, automatic token refresh, and a revoked refresh token marks the connection for reconnecting.
- Connector actions: `airtable_upsert`, `smtp_send_email` (approval-gated), `http_get`, `http_send` and `google_sheets_append_row`. The engine decrypts the step's connection just before it runs, and only from the same workspace.
- SSRF protection for outbound HTTP: public addresses only, DNS-resolved checks, no redirects and no credentials in URLs.
- Inbound webhooks: per-workflow secret URLs, HMAC signatures (AutoFlow with a replay window, or Shopify), duplicate-delivery idempotency, a 256 KB limit, and only published webhook-triggered workflows.
- Migration 0003 (connections, webhook_endpoints).

## V11: AI workflow builder
- `POST /workspaces/{id}/workflows/ai-draft`: plain-language request → validated workflow draft, with clarifying questions, assumptions and unsupported apps; optional save as a draft workflow.
- The AI sees the live action catalogue and an example. Its output passes the standard validator, with up to 2 repair rounds that feed the validator's errors back.
- Model router (`autoflow.ai.providers`): Gemini and Claude (`claude-opus-5-5`, server-side refusal fallbacks) with ordered fallback when a provider fails.
- Tests can no longer pick up real credentials from `backend/.env`.
- Verified live with Gemini: a five-step enquiry workflow was drafted valid on the first attempt.

## V10: Workflow engine
- Workflows are defined as data: a trigger, ordered steps, `{{ }}` references to the trigger and earlier outputs, and `when` conditions for branching.
- Action registry with input/output specs and safety flags (side effect, idempotent, requires approval). The existing capabilities became actions: classify, quote, compose, send, save customer and log.
- Strict definition validation; mandatory approvals cannot be switched off.
- Versioning: draft, publish, new draft on edit, and rollback to any version. Workflows can be archived.
- Test mode (side effects simulated) vs live mode (published version only).
- Executor:
  - retries with exponential backoff, per-step timeouts, and non-retryable input errors;
  - resumes from the failed step and never repeats succeeded steps;
  - uncertain non-idempotent side effects become `needs_attention` instead of being retried blindly;
  - honours the `Idempotency-Key` header, and supports cancel and approval-gated steps.
- Built-in template: customer enquiry triage.
- New tables: workflows, workflow_versions, workflow_executions and step_executions. Approvals can now gate an execution step.
- SQLite runs in WAL mode (commits about 30× faster); added a constraint naming convention for future migrations.

## V9: Core foundation (accounts, workspaces, tenant isolation)
- Moved storage to SQLAlchemy 2 with Alembic migrations. SQLite is the default and PostgreSQL is set via `DATABASE_URL`. Migrations run automatically on start.
- New tables: users, workspaces, memberships (roles: viewer, member, admin, owner) and access tokens.
- Customers, workflow runs and approvals now belong to a workspace. Every query is scoped to it, and the same customer email can exist in different workspaces.
- Auth: register (creates an owned workspace), login (bearer token, stored only as a hash), logout (revocation) and token expiry. Passwords are hashed with scrypt.
- API reorganized into routers; all data routes live under `/workspaces/{id}/…` with role checks. Unknown or foreign workspaces return 404.
- Approvals record which user decided them.
- The CLI runs in a "local" workspace. Only that workspace writes local files or uses the `.env` Airtable account, so one tenant's data never reaches another's CRM.
- Tests cover isolation, roles, token expiry and revocation, and run the real migrations.

## V8: Approvals as data
- New `approvals` table and approval service (`autoflow.approvals`).
- Runs without a terminal queue AI classifications and emails as pending approvals.
- API: list, view, approve (with optional category correction) and reject approvals.
- Safety: decisions are atomic and final, emails are blocked until the customer's classification is reviewed, and a correction regenerates the pending email.
- Approval decisions are written to the activity log.
- Added `.gitattributes` to normalize line endings.

## V7: REST API
- FastAPI application (`autoflow.api`) with interactive docs at `/docs`.
- Endpoints for health, customers (with category filter), customer detail, and listing and starting workflow runs.
- The pipeline can run without a terminal (`run(interactive=False)`) and returns a run summary.
- `AUTOFLOW_INPUT_CSV` setting; API host/port settings.

## Repository restructure
- Moved into a monorepo layout (`backend/`, `frontend/`, `docs/`) with an installable `autoflow` package.
- Split `main.py` into a `run()` pipeline and separate modules for Airtable, exchange rates, the activity log and config.
- Generated files now go to `backend/data/output/` and are git-ignored.
- Fixed: the `workflow_runs` table was never created (it ran on a closed connection).
- Removed a duplicate `log_airtable_event` definition.
- `requirements.txt` re-encoded from UTF-16 to UTF-8; added `GEMINI_MODEL` and `AI_CLASSIFICATION_ENABLED` to `.env.example`.
- Added pytest tests.

## V6: Database persistence
SQLite storage, upsert by email, and workflow-run history.

## V5: AI-assisted classification
Gemini classification with reasons, human approval or correction, and a keyword-rule fallback.

## V4: Controlled email automation
Personalized previews, human approval, Gmail test sending, and a safety switch.

## V3: Airtable synchronization
Create/update by email, validation, pagination, and logging.

## V2: API enrichment
EUR→USD reference rate and sample quotes for Sales enquiries.

## V1: CSV processing
Categorize enquiries, write the processed CSV, and log activity.
