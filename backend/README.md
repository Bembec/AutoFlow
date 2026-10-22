# AutoFlow backend

Python package `autoflow`: a multi-tenant API plus the customer-enquiry workflow.

The workflow:

1. Read enquiries from `data/sample/customers.csv`
2. Classify each one as Sales / Support / Other — Gemini with human review, or keyword rules as a fallback
3. Add a EUR→USD sample quote to Sales enquiries (Frankfurter API)
4. Save results to the database, in the workspace that ran it
5. Ask a human to approve emails before anything is sent (Gmail, test recipient only)
6. Local workspace only: write CSV/previews and sync Airtable using `.env` credentials
7. Write the activity log and record the workflow run

## Commands

| Task | Command |
| --- | --- |
| Run the workflow (local workspace) | `python -m autoflow` (or `autoflow`) |
| Start the API server | `python -m autoflow.api`, then open http://127.0.0.1:8000/docs |
| Run the tests | `pytest` |
| Apply database migrations | `alembic upgrade head` (also runs automatically on start) |
| Create a migration after changing `storage/models.py` | `alembic revision --autogenerate -m "describe change"` |
| Check Airtable access | `python scripts/checks/check_airtable.py` |
| Check the exchange-rate API | `python scripts/checks/check_exchange_rate.py` |
| Check Gemini access | `python scripts/checks/check_gemini.py` |

`scripts/checks/create_airtable_test_record.py` writes one test record to Airtable.

## Accounts and workspaces (V9)

- Each business works in its own **workspace**. Customers, runs and approvals belong to one workspace, and every query filters by it.
- Registering creates a user plus their own workspace, where they are the `owner`.
- Roles: `viewer` (read) < `member` (run workflows, decide approvals) < `admin` (add members) < `owner`. Nobody can grant a role higher than their own.
- Login returns a bearer token (valid `ACCESS_TOKEN_TTL_HOURS`). Only a SHA-256 hash of it is stored; passwords are hashed with scrypt.
- Asking for a workspace you are not a member of returns `404`, so other workspaces' ids are not revealed.

## REST API

Send `Authorization: Bearer <token>` on every request except health, register and login.

| Method | Path | Role | Description |
| --- | --- | --- | --- |
| GET | `/health` | — | Service status and version |
| POST | `/auth/register` | — | Create an account and its workspace |
| POST | `/auth/login` | — | Get an access token |
| POST | `/auth/logout` | any | Revoke the current token |
| GET | `/me` | any | Current user and their workspaces |
| POST | `/workspaces` | any | Create another workspace (you become owner) |
| GET | `/workspaces/{id}/members` | viewer | List members |
| POST | `/workspaces/{id}/members` | admin | Add an existing user with a role |
| GET | `/workspaces/{id}/customers?category=Sales` | viewer | Stored customers |
| GET | `/workspaces/{id}/customers/{customer_id}` | viewer | One customer |
| GET | `/workspaces/{id}/workflow-runs?limit=10` | viewer | Recent runs |
| POST | `/workspaces/{id}/workflow-runs` | member | Run the workflow; decisions are queued as approvals |
| GET | `/workspaces/{id}/approvals?status=pending&kind=email` | viewer | Approval queue |
| GET | `/workspaces/{id}/approvals/{approval_id}` | viewer | One approval |
| POST | `/workspaces/{id}/approvals/{approval_id}/approve` | member | Approve (body `{"category": "Support"}` corrects a classification) |
| POST | `/workspaces/{id}/approvals/{approval_id}/reject` | member | Reject; nothing is changed or sent |

## Workflow engine (V10)

A workflow is **data**: a trigger plus ordered steps, each calling a registered action.

```json
{
  "trigger": {"type": "manual", "sample_payload": {"name": "Ada", "email": "ada@example.com", "message": "Price?"}},
  "steps": [
    {"id": "classify", "action": "classify_enquiry", "inputs": {"message": "{{trigger.message}}"}},
    {"id": "quote", "action": "exchange_rate_quote", "inputs": {"amount_eur": 100},
     "when": {"left": "{{steps.classify.output.category}}", "op": "eq", "right": "Sales"},
     "retry": {"max_attempts": 3, "backoff_seconds": 2}, "timeout_seconds": 20},
    {"id": "send", "action": "send_email",
     "inputs": {"to": "{{trigger.email}}", "subject": "Hi", "body": "Thanks!"}}
  ]
}
```

- **Actions:** `classify_enquiry`, `exchange_rate_quote`, `compose_email`, `send_email` (always needs approval), `save_customer` and `log_activity`. `GET /actions` lists them with their inputs and outputs.
- **Validation:** before saving, the engine checks for unknown actions or inputs, missing inputs, duplicate step ids, references to later steps, and attempts to switch off a mandatory approval.
- **Versions:** a new workflow is a draft. Publishing freezes it, and editing a published workflow starts a new draft. `POST …/publish {"version": 1}` rolls back.
- **Test vs live:** test runs use the draft and *simulate* side effects. Live runs use the published version.
- **Reliability:**
  - Retries use exponential backoff, and timeouts are enforced.
  - Bad input fails at once, without retrying.
  - Succeeded steps are never repeated, so a retry continues from the failed step.
  - If a non-idempotent side effect (sending email) times out or is interrupted, the execution becomes `needs_attention`. It can only be retried after someone confirms the step did not complete.
  - An `Idempotency-Key` header returns the existing execution instead of starting a duplicate.
- **Approvals:** live steps that need approval pause the execution (`waiting_approval`). Approving resumes it, while rejecting or cancelling stops it.

| Method | Path | Role | Description |
| --- | --- | --- | --- |
| GET | `/actions` | — | Action catalogue |
| GET | `/templates` | — | Ready-made workflows |
| GET/POST | `/workspaces/{id}/workflows` | viewer/member | List / create |
| POST | `/workspaces/{id}/workflows/from-template` | member | Install a template (`{"template": "customer-enquiry-triage"}`) |
| GET/PATCH | `/workspaces/{id}/workflows/{wf}` | viewer/member | View / edit (edits change the draft) |
| POST | `/workspaces/{id}/workflows/{wf}/publish` | member | Publish draft, or `{"version": n}` to roll back |
| POST | `/workspaces/{id}/workflows/{wf}/archive` | member | Archive |
| POST | `/workspaces/{id}/workflows/{wf}/executions` | member | Run: `{"mode": "test"\|"live", "payload": {...}}`, optional `Idempotency-Key` header |
| GET | `/workspaces/{id}/executions?status=failed` | viewer | Run history |
| GET | `/workspaces/{id}/executions/{ex}` | viewer | One execution, step by step |
| POST | `/workspaces/{id}/executions/{ex}/cancel` | member | Cancel |
| POST | `/workspaces/{id}/executions/{ex}/retry` | member | Retry from the failed step (`{"confirm_not_completed": true}` for `needs_attention`) |

## Billing and usage (V15)

**Billable task:** one step that **succeeds**, in a **live** run, and **calls an app or AI model**. Failed steps, retries, test runs and local steps (compose, log, save) are free. Rules-only classification is free too. Each billable step creates one `billable_events` row, unique per step run, so nothing is billed twice.

| Plan | $/month | Tasks/month | Workflows | Seats |
| --- | --- | --- | --- | --- |
| Free | 0 | 500 | 5 | 1 |
| Starter | 29 | 5,000 | 20 | 2 |
| Growth | 99 | 25,000 | unlimited | 5 |
| Business | 299 | 100,000 | unlimited | 20 |
| Enterprise | custom | custom | unlimited | unlimited |

These are the roadmap's starting proposals, defined in `billing/plans.json`; override them with `AUTOFLOW_PLANS_FILE`.

- **Hard cap:** reaching the included tasks pauses *billable* steps. Free plans always have the cap; owners on paid plans can turn it off.
- **Alerts:** the billing summary warns at 80% and 100% of included tasks, when the projected usage will exceed the plan, and when a payment has failed.
- **Stripe:**
  - `POST …/billing/checkout {"plan"}` returns a Checkout URL, and `POST …/billing/portal` returns the customer-portal URL (cards, invoices, downgrades, cancellation).
  - `POST /billing/stripe-webhook` verifies `Stripe-Signature`, applies each event once, and handles checkout, subscription create/update/delete (plan from the price id), `invoice.payment_failed` (→ `past_due`, plan kept during the grace period) and `invoice.paid`.
- **Manual billing (pilots):** staff listed in `AUTOFLOW_STAFF_EMAILS` can set a plan with `PUT /admin/workspaces/{id}/plan`. Customers cannot change their own plan except through payment.

## AI steps and safety controls (V13)

**AI actions**: `ai_extract` (named fields from emails/documents), `ai_classify` (into *your* categories), `ai_summarize`, `ai_draft_reply`, `ai_translate`.

- **Containment:** AI steps only produce data. They have no tools and cannot act. Their JSON is validated against what the step asked for: extraction returns only the requested fields, and classification cannot invent categories.
- **Prompt-injection guard:** untrusted text is fenced inside a random boundary that the sender cannot close, and the model is told it is data, never instructions. Injection phrasing is also detected. A suspected injection always goes to a human in live mode.
- **Confidence review:** live AI results below `review_below_confidence` (default 0.7 for `ai_extract`, `0` disables) pause for review. The reviewer approves, or corrects the output with `{"output": {"data": {...}}}`, and later steps use the corrected data.

**Emergency stop and policies**

| Method | Path | Role | Effect |
| --- | --- | --- | --- |
| POST | `/workspaces/{id}/emergency-stop` | admin | Stop all automations, cancel open runs and pending step approvals, block webhooks |
| POST | `/workspaces/{id}/resume-automations` | admin | Lift the stop |
| POST | `/workspaces/{id}/workflows/{wf}/pause` · `/resume` | member | Stop one workflow (test runs still allowed) |
| GET / PATCH | `/workspaces/{id}/policies` | viewer / admin | Daily limits and today's usage |

Policies cover daily limits on executions (1000), AI calls (200) and live emails (100), plus `approve_all_side_effects`, which requires human approval for every side effect. These are enforced by the engine and cannot be bypassed by a workflow.

## Integrations (V12)

**Connections** hold a workspace's own credentials for an app. Secrets are encrypted with Fernet (`AUTOFLOW_SECRET_KEYS`, rotatable), only decrypted when a step needs them, and never returned by the API (only masked, e.g. `pat…3456`). Only admins can manage connections.

| App | Provider | Auth | Actions |
| --- | --- | --- | --- |
| Airtable | `airtable` | API token | `airtable_upsert` (create/update, matched on a field) |
| Email (Gmail etc.) | `smtp` | App password | `smtp_send_email` (always needs approval; `EMAIL_SEND_ENABLED` switch; optional `test_recipient` redirect) |
| Any REST API | `http` | API-key header | `http_get`, `http_send` |
| Google Sheets | `google` | OAuth2 (auto-refresh) | `google_sheets_append_row` |

- **Step inputs:** steps name their connection: `"inputs": {"connection": "crm", ...}`. A workflow can only use connections from its own workspace.
- **OAuth:** `POST …/connections/oauth/google/start` returns the consent URL. Its `state` is encrypted and expires after 10 minutes. Google redirects to `/oauth/callback/google`, which stores the tokens. Access tokens are refreshed before expiry. If a refresh token is revoked, the connection is marked `error` ("reconnect"), so the step fails instead of retrying forever.
- **HTTP safety:** `http_*` actions only reach public addresses. Loopback, private, link-local and cloud-metadata IPs are refused even behind DNS names, and redirects are not followed.

**Webhooks** let other apps start a published workflow whose trigger is `webhook`:

- `POST …/workflows/{wf}/webhook` returns a URL and a secret, shown once. Use `{"signature_scheme": "shopify", "secret": "<app secret>"}` for Shopify.
- The sender signs every request: `X-AutoFlow-Timestamp` plus `X-AutoFlow-Signature: sha256=HMAC(secret, "<ts>.<body>")`, with a 5-minute replay window. Shopify uses its `X-Shopify-Hmac-Sha256` header instead.
- Duplicate deliveries (`Idempotency-Key`, `X-Shopify-Webhook-Id`, `X-Request-Id`) return the first execution instead of starting another.

| Method | Path | Role |
| --- | --- | --- |
| GET | `/integrations` | — |
| GET / POST | `/workspaces/{id}/connections` | viewer / admin |
| PUT | `/workspaces/{id}/connections/{c}/secrets` | admin |
| DELETE | `/workspaces/{id}/connections/{c}` | admin |
| POST | `/workspaces/{id}/connections/oauth/{provider}/start` | admin |
| GET | `/oauth/callback/{provider}` | — (signed state) |
| GET / POST / DELETE | `/workspaces/{id}/workflows/{wf}/webhook` | viewer / member / member |
| POST | `/hooks/{public_id}` | — (signature) |

## AI workflow builder (V11)

`POST /workspaces/{id}/workflows/ai-draft` (member)

```json
{"request": "When a customer sends an enquiry, classify it, quote sales leads in USD and email a reply",
 "answers": [], "save": false}
```

- **What comes back:**
  - `status: "ready"` with a validated `definition`; or
  - `status: "needs_details"` with `questions`. Send them back in `answers` to continue.

  The reply also lists the AI's `assumptions`, plus any `unsupported` apps it could not build with.
- **Validation:** every draft goes through the same validator as hand-written workflows. The AI gets up to 2 repair attempts with the validator's errors. It never invents actions, and it cannot switch off mandatory approvals.
- **Drafting only:** with `"save": true` a valid draft is stored as a **draft** workflow. A person still test-runs and publishes it.
- **Model router (`autoflow.ai.providers`):** providers are tried in `AI_PROVIDER_ORDER` (Gemini, then Claude `claude-opus-5-5` with server-side refusal fallbacks). A provider without a key is skipped, and when one fails the next is used. If none is configured, the endpoint returns `503`.

### Human approval rules (V8)

- AI classifications and outgoing emails made without a terminal wait as **pending approvals**.
- Re-running the workflow refreshes a pending approval instead of duplicating it.
- An email cannot be approved while that customer's classification is unreviewed.
- Correcting a category regenerates the pending email with the right wording.
- Each approval is decided exactly once (a second attempt returns `409`), so an email is never sent twice. The deciding user is recorded.
- `EMAIL_SEND_ENABLED` and the test-recipient redirect still apply to approved emails.

## Configuration

All settings live in `backend/.env` (see `.env.example`). The database defaults
to SQLite at `data/output/autoflow.db`; set `DATABASE_URL` for PostgreSQL.
Generated files go to `data/output/`, or to `AUTOFLOW_DATA_DIR` if set.
