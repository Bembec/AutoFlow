# Architecture

## Current (V9)

```
Client ──HTTPS──▶ FastAPI (autoflow.api)
                   ├─ auth: bearer token → user
                   ├─ require_role: user + workspace_id → membership (404 if none)
                   └─ routes ──▶ services (pipeline, approvals, accounts)
                                   └─▶ repositories (storage/*): every query filtered by workspace_id
                                         └─▶ SQLAlchemy ──▶ SQLite (dev) / PostgreSQL (prod)
```

| Package | Responsibility |
| --- | --- |
| `autoflow.api` | HTTP layer: routers, request/response schemas, auth and role dependencies |
| `autoflow.accounts` | Users, workspaces, memberships, password hashing, access tokens |
| `autoflow.pipeline` | The customer-enquiry workflow, run per workspace |
| `autoflow.approvals` | Human-in-the-loop decisions (classification, email) |
| `autoflow.storage` | Models, repositories, Alembic migrations |
| `autoflow.classification`, `emails`, `integrations` | AI and external services |

### Tenant isolation rules

1. Every business table has a `workspace_id`.
2. Repository functions take `workspace_id` as a required argument and always filter by it.
3. API routes get `workspace_id` only through the `require_role` dependency, which checks membership first.
4. Credentials from `.env` (Airtable) are used only by the local CLI workspace.

## Target (from the roadmap)

Five layers: client apps → security gateway → core engine → AI layer → data layer.
The AI builder only *drafts* workflows; the workflow engine *runs* them, so
every run is predictable, logged and retryable.

| Layer | Planned tools |
| --- | --- |
| Web front end | Next.js, TypeScript, Tailwind, React Flow |
| Back end | Python (FastAPI), continuing from this codebase |
| Workflow engine | Temporal (durable runs), or a simpler queue for the MVP |
| AI models | Several providers behind one router |
| Data | PostgreSQL (+ pgvector), Redis, S3-compatible storage |

## Workflow engine (V10)

```
definition (JSON) ──validate──▶ WorkflowVersion (draft → published → archived)
                                      │
start (test|live, payload, Idempotency-Key)
                                      ▼
                         WorkflowExecution ──▶ StepExecution × n
                                      │
for each step: cancelled? → done/skipped? → `when` → render inputs
            → approval gate (live) → mark running + commit → action (retry/timeout)
```

`autoflow.engine` modules: `definition` (schema and validation), `templating`
(`{{ }}` references and conditions), `actions` (registry), `executor`
(execution and recovery), `service` (workflows, versions, starting runs),
`templates`.

Executions currently run inside the API request. Because all state lives
in the database, a background worker (or Temporal) can take over
`executor.execute` later without changing the data model.

## AI builder (V11)

```
plain-language request ──▶ prompt (action catalogue + example + answers)
                       ──▶ model router (Gemini → Claude, fallback on failure)
                       ──▶ JSON ──▶ WorkflowDefinition validator
                                     │ invalid: errors sent back (≤ 2 repairs)
                                     │ valid
                                     ▼
                           draft workflow (never auto-published)
```

## Next technical steps

1. **V12, integrations:** per-workspace encrypted credentials, webhooks with signature checks, and first connectors.
2. **V13, AI steps and safety:** document/email extraction with confidence scores, prompt-injection guard, emergency stop, and action limits.
3. **Later:** a background worker for executions and schedule triggers.
