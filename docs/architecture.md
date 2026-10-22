# Architecture

## Current (V6)

A single-process Python workflow (`backend/src/autoflow/pipeline.py`) runs
these steps in order and asks for human approval in the terminal:

```
CSV input → classify (Gemini + human review | keyword rules) → exchange-rate quotes
          → SQLite + CSV → email previews → approved test email (Gmail)
          → Airtable sync → activity log + workflow_runs record
```

Each external service has its own module (`classification/`, `emails/`,
`integrations/`, `storage/`), so the steps can later become reusable
workflow-engine actions.

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

1. Expose the stored data and workflow runs through a FastAPI layer (V7).
2. Replace terminal `input()` approvals with approval records the API and dashboard can act on.
3. Turn each pipeline step into an engine action with idempotency keys and retries.
