# Operations runbook

How AutoFlow is deployed, monitored, backed up and recovered.

## Components

| Process | Command | Scale |
| --- | --- | --- |
| API | `uvicorn autoflow.api.app:app` (Docker default command) | Horizontally (stateless) |
| Worker | `python -m autoflow.worker` | Any number; schedule slots are idempotent |
| Web app | `node server.js` (Next.js standalone) | Horizontally (stateless) |
| Database | PostgreSQL 17 | Managed service recommended |
| Migrations | `alembic upgrade head` | Once per deploy, before API/worker start |

`docker compose up --build` runs the whole stack locally (see `docker-compose.yml`).

## Environments

`AUTOFLOW_ENV` is `development`, `staging` or `production`. Outside development, the API and worker **refuse to start** unless:

- `AUTOFLOW_SECRET_KEYS` is set (from a secrets manager, never a file);
- `DATABASE_URL` points to PostgreSQL;
- `AUTOFLOW_PUBLIC_URL` uses https;
- and, in production, `EMAIL_TEST_RECIPIENT` is unset.

Staging and production also differ in a few defaults:

- **Migrations:** they do not run automatically (`AUTOFLOW_AUTO_MIGRATE=false`).
- **Security headers:** HSTS is sent.
- **Docs:** `/docs` is disabled in production.

Staging and production have separate databases, secret keys, Stripe accounts (test vs live) and OAuth clients. Never point staging at production data.

**Demo workspace.** `python -m autoflow.demo` creates "Demo Mug Shop" for staging, sales demos and screenshots. It has:
- business details;
- the three e-commerce templates, switched on;
- eight weeks of past runs and invoices;
- one email waiting for approval.

Its mailbox points at an unreachable host, so nothing is ever sent. Running the command again changes nothing. Sign in as `demo@autoflow.example` / `demo-password-2026`, or pass `--email` and `--password`. Never run it against production.

**Feature flags** (`backend/src/autoflow/features.py`) let you switch features without a deploy:
- the current flags are `ai_builder`, `insights_suggestions`, `connection_checks`, `help_assistant`, and two that are in development and off by default: `smarter_logic` and `mcp_tools`;
- set them per environment with `AUTOFLOW_FEATURES="smarter_logic=on,ai_builder=off"`;
- override them for one workspace with `PUT /staff/workspaces/{id}/features` (null removes an override);
- the server enforces them, and the app hides what is off;
- unfinished work ships behind a flag that is off by default.

## Deploy

1. CI must be green: tests on SQLite and PostgreSQL, migration check, frontend type check/lint/build, and image builds.
2. Build and tag images with the git commit, e.g. `autoflow-api:<sha>` and `autoflow-web:<sha>`.
3. **Back up the database** (see below).
4. Run migrations with the new image: `alembic upgrade head`.
5. Roll out the API and worker, then the web app.
6. Check that `GET /ready` returns `200` with `"schema": "current"`, sign in, and run a test execution.

Migrations must stay backwards-compatible for one release (add columns before using them; remove them a release later), so the old version keeps working while the new one rolls out.

## Rollback

- **Code only:** redeploy the previous image tags.
- **Schema change:** `alembic downgrade <previous revision>` (each migration has a tested downgrade), then redeploy the previous images. If a downgrade would lose data, restore from the pre-deploy backup instead.

## Monitoring

| Signal | Where | Alert when |
| --- | --- | --- |
| Liveness | `GET /health` | not 200 for 1 minute |
| Readiness | `GET /ready` (database and schema) | 503 |
| Request logs | stdout, `request_id=` on every line, echoed as `X-Request-ID` | 5xx rate > 1% |
| Failed runs | `GET /workspaces/{id}/executions?status=failed` / dashboard | sudden rise |
| `needs_attention` runs | executions list | any (a human must check) |
| Worker | `Worker tick failed` log lines | repeated |

Point an uptime checker at `/health` and `/ready`, and ship logs to your log platform. For error tracking, Sentry can be added at the ASGI layer.

## Backups and restore

- **Database:** use the managed PostgreSQL's daily snapshots with point-in-time recovery (at least 7 days), plus `pg_dump -Fc` before every deploy.
- **Secret keys:** back up `AUTOFLOW_SECRET_KEYS` separately (in the secrets manager). Without them, stored credentials cannot be decrypted.
- **Test a restore every month:**
  ```bash
  pg_restore --clean --no-owner -d autoflow_restore_test backup.dump
  DATABASE_URL=postgresql+psycopg://…/autoflow_restore_test alembic current
  ```
  Then start an API against it and check `/ready`.

## Secret key rotation

1. Generate a new Fernet key.
2. Set `AUTOFLOW_SECRET_KEYS=<new>,<old>` and deploy. New writes use the new key, and both keys decrypt.
3. Re-encrypt stored secrets (`autoflow.security.vault.rotate`), then remove the old key.

## Incident response

1. **Stop the damage.** If automations are misbehaving (wrong emails, runaway costs), use the workspace **emergency stop** (Settings, or `POST /workspaces/{id}/emergency-stop`). This cancels runs and blocks webhooks. For a platform-wide problem, scale the worker to 0 and put the API in maintenance.
2. **Find it.** Search logs by `request_id`, look at the affected executions step by step, and check `/ready`.
3. **Fix and recover.**
   - **Failed runs** retry from the failed step.
   - **`needs_attention` runs** need a human to confirm that the uncertain step did not happen before retrying.
4. **Tell customers.** Update the status page, and email the affected workspace owners.
5. **Write it up** within 5 working days: timeline, cause, and what prevents a repeat.

## Trust and safety

- **Abuse reports** arrive through the public form at `/report-abuse` (`POST /abuse-reports`, at most 5 per IP address per hour). Every SMTP email carries `X-AutoFlow-Workspace` and `X-Report-Abuse` headers. Staff, listed in `AUTOFLOW_STAFF_EMAILS`, review reports at `GET /staff/abuse-reports` and close them with `POST /staff/abuse-reports/{id}/close`.
- **Suspend a workspace** that breaks the acceptable-use rules: `POST /staff/workspaces/{id}/suspend` with a reason. It stops all automations, and the owner can't resume them. To restore the workspace, use `POST /staff/workspaces/{id}/unsuspend`.
- **New accounts** get lower daily limits for 7 days. Lift them early for a known customer with `POST /staff/workspaces/{id}/trust`.
- **Blocked phishing** is logged as the `outbound.blocked` audit event. Check these events when reviewing a report.
- **The AI budget** is estimated as AI calls x `AUTOFLOW_AI_COST_PER_CALL_USD` (default 0.01) against `ai_budget_usd_month` in `plans.json`. Tune both from real provider bills.

## Reliability evidence

- `backend/tests/test_duplicate_soak.py` pushes many shop orders through the order → invoice template in queue mode while forcing the usual causes of duplicates:
  - repeated webhooks;
  - redeliveries;
  - double approvals;
  - mail-server failures;
  - worker crashes mid-send.

  It then counts the real effects (invoices, emails, billable events). CI runs 60 orders.
- For the MVP gate, run 1,000 and keep the report:
  `AUTOFLOW_SOAK_RUNS=1000 AUTOFLOW_SOAK_REPORT=../docs/evidence/duplicate-soak.md pytest tests/test_duplicate_soak.py`
  This takes about 6 minutes on SQLite. Repeat it on PostgreSQL in staging before the gate.
- **Compensation tools:**
  - void an invoice: `POST /workspaces/{id}/invoices/{invoice_id}/void`, or the `void_invoice` step;
  - confirm that an uncertain step happened: `POST /executions/{id}/confirm-done`. It never re-runs the step; `retry` covers the opposite case.
- **Connection health:** `POST /connections/{id}/check` runs a read-only login or fetch. A connection that breaks, during a check or a run, alerts the owner once. Network errors don't mark a connection broken.

## Help assistant

The in-app help assistant answers only from the help articles. The server ships a copy of `docs/help` in `backend/src/autoflow/help_docs`. After editing any help article, run `python backend/scripts/sync_help.py`; a test fails if the copies differ. Questions don't count against the customer's AI limits, and each workspace can ask up to 30 an hour.

## Customer data requests

- **Export:** the workspace owner downloads a full JSON export from `GET /workspaces/{id}/export`. Secrets are never included.
- **Delete a workspace:** `DELETE /workspaces/{id}` with the workspace name typed to confirm. It cancels open runs, and the database cascades remove all its data.
- **Close an account:** `DELETE /me` with the user's password. It deletes the user and any workspaces only they belong to. A sole owner of a shared workspace must hand over ownership first.
- Database backups expire on their normal retention schedule.
