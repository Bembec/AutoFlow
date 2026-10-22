# Architecture

## System overview (V16)

```
Browser ──▶ Web app (Next.js) ──/api, /hooks──▶ API (FastAPI) ──▶ PostgreSQL
                                                  │  ▲
Other apps ──signed webhooks──────────────────────┘  │
                                                     │
Worker (python -m autoflow.worker) ── schedules ─────┘
                                                  │
                         AI providers (Gemini, Claude) · Apps (Airtable, Google, SMTP, REST)
```

Every request passes through the same layers:

```
HTTP middleware (request id, security headers, sign-in rate limit)
  → auth (bearer token → user) → require_role (user + workspace → membership, 404 if none)
  → route → service (engine, approvals, billing, integrations, accounts)
  → repositories / models (every query filtered by workspace_id)
  → SQLAlchemy → PostgreSQL (SQLite in development)
```

## Packages

| Package | Responsibility |
| --- | --- |
| `autoflow.api` | Routers, schemas, auth/role dependencies, middleware |
| `autoflow.accounts` | Users, workspaces, memberships and roles, password hashing, access tokens |
| `autoflow.engine` | Workflow definitions and validation, `{{ }}` templating, action registry, executor, versions, limits, templates |
| `autoflow.ai` | Model router (Gemini/Claude with fallback), AI workflow builder, AI steps |
| `autoflow.integrations` | Connections and their catalogue, OAuth2, webhooks, connector actions |
| `autoflow.security` | Secrets vault (Fernet, rotation), prompt-injection guard, SSRF protection |
| `autoflow.billing` | Plans, billable-task metering, plan limits, Stripe |
| `autoflow.approvals` | Human decisions: classifications, emails, step gates, AI result reviews |
| `autoflow.storage` | Models, repositories, Alembic migrations |
| `autoflow.worker` | Scheduled workflows and housekeeping |
| `autoflow.pipeline` | The original V1–V6 enquiry workflow (CLI and legacy endpoint) |

## Tenant isolation

1. Every business table has a `workspace_id`.
2. Repository and service functions take `workspace_id` as a required argument and filter by it.
3. Routes receive the workspace only through `require_role`, which checks membership first. Foreign workspaces return 404, so their existence is never revealed.
4. Connector steps decrypt credentials only from their own workspace's connections. `.env` credentials are used only by the local CLI workspace.
5. Tests cover cross-workspace reads, writes, approvals, executions and connections.

## Workflow engine

```
definition (JSON) ──validate──▶ WorkflowVersion (draft → published → archived)
                                      │
start (test|live, payload, Idempotency-Key)  ← API · webhook · worker schedule
                                      ▼
                         WorkflowExecution ──▶ StepExecution × n
                                      │
for each step:
  cancelled? → done/skipped? → `when` → render inputs
  → approval gate (live; mandatory for sensitive actions, or every side effect by policy)
  → daily limits + plan cap → mark running + commit
  → action (credentials, timeout, retry/backoff)
  → review if low confidence or suspected injection (live AI steps)
  → success + billable event in one commit
```

**Guarantees**

- Succeeded steps are never repeated.
- A non-idempotent side effect whose outcome is unknown becomes `needs_attention` and is not retried blindly.
- Test runs simulate side effects.
- Approvals are decided exactly once.

Executions run in the API process. All state lives in the database, so a queue-backed worker, or Temporal, can take over `executor.execute` without changing the data model.

## AI

```
plain-language request ──▶ prompt (action catalogue + example + answers)
                       ──▶ model router (Gemini → Claude, fallback on failure)
                       ──▶ JSON ──▶ WorkflowDefinition validator
                                     │ invalid: errors sent back (≤ 2 repairs)
                                     ▼ valid
                           draft workflow (never auto-published)
```

AI steps fence untrusted text inside a random boundary and validate replies against exactly what was requested. Their results carry `confidence` and `injection_suspected` for the executor's review rule.

## Roadmap stack vs. implementation

| Layer | Roadmap | Now |
| --- | --- | --- |
| Web front end | Next.js, TypeScript, Tailwind, React Flow | ✔ same |
| Back end | NestJS or FastAPI | FastAPI |
| Workflow engine | Temporal, or BullMQ for the MVP | Own DB-backed engine; worker for schedules |
| AI models | Several providers behind one router | Gemini + Claude router |
| Data | PostgreSQL (+ pgvector), Redis, S3 | PostgreSQL (SQLite in dev). pgvector, Redis and S3 when features need them |
| Security | Secrets vault (KMS/Vault), Auth0/Clerk | Fernet vault with rotation; own auth (swap for Auth0/Clerk for SSO) |
| Billing | Stripe | Stripe Checkout, portal and webhooks; manual pilot plans |
| DevOps | Docker, GitHub Actions, AWS/GCP | Docker, compose, GitHub Actions. Cloud target to be chosen |

See [roadmap status](roadmap/status.md) for what remains.
