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

## Customer data requests

- **Export:** the workspace owner downloads a full JSON export from `GET /workspaces/{id}/export`. Secrets are never included.
- **Delete a workspace:** `DELETE /workspaces/{id}` with the workspace name typed to confirm. It cancels open runs, and the database cascades remove all its data.
- **Close an account:** `DELETE /me` with the user's password. It deletes the user and any workspaces only they belong to. A sole owner of a shared workspace must hand over ownership first.
- Database backups expire on their normal retention schedule.
