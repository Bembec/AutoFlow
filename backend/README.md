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
