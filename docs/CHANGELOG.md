# Changelog

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
