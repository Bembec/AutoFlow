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

## Next technical steps

1. **V10, workflow engine:** workflow definitions (steps as data), step runs, retries, timeouts, idempotency keys, and draft/test/publish modes. The current pipeline becomes the first workflow built from engine actions.
2. **V11, AI builder:** plain-language request → validated workflow definition.
3. **V12, integrations:** per-workspace encrypted credentials, webhooks with signature checks, and first connectors.
