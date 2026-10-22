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
