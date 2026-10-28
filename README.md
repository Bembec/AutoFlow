# Luphina

*Turning Challenges Into Progress.*

> **Picking up the work?** Start with [docs/RESUME-HERE.md](docs/RESUME-HERE.md) (where we stopped and what to do next) and [docs/DECISIONS-NEEDED.md](docs/DECISIONS-NEEDED.md) (the owner's open decisions).

Luphina helps businesses simplify repetitive work, connect their tools, and turn everyday processes into intelligent workflows. Describe a process in plain words and get a working, AI-powered automation, with no developers needed.

Luphina was developed under the working name **AutoFlow**, which internal names (the `autoflow` package, `AUTOFLOW_*` settings, `X-AutoFlow-*` headers) still use. See the [brand guide](docs/brand/README.md).

This monorepo holds the product as described in the [product roadmap](docs/roadmap/README.md):

- **Accounts and workspaces:** each business's data is isolated, with roles from viewer to owner.
- **Workflow engine:** retries, timeouts, idempotency, approvals, versioning, and test vs live runs.
- **AI workflow builder:** plain words in, validated workflow out, through a Gemini/Claude router.
- **AI steps:** extract, classify, summarise, reply and translate, with prompt-injection defences and confidence review.
- **Integrations:** encrypted per-workspace connections (Airtable, SMTP, REST APIs, Google OAuth) and signed webhooks (including Shopify).
- **Safety controls:** emergency stop, daily limits, and "approve everything" mode.
- **Web app:** dashboard with time saved, canvas, run history, approvals inbox, connected apps and settings.

## Repository layout

```
AutoFlow/
├── backend/                  Python API and workflow engine (FastAPI, SQLAlchemy, Alembic)
│   ├── src/autoflow/
│   │   ├── api/              HTTP routes, schemas, auth and role dependencies
│   │   ├── accounts/         Users, workspaces, memberships, tokens
│   │   ├── engine/           Definitions, actions, executor, versions, limits, templates
│   │   ├── ai/               Model router, AI builder, AI steps
│   │   ├── integrations/     Connections, OAuth, webhooks, connector actions
│   │   ├── security/         Secrets vault, prompt-injection guard, SSRF protection
│   │   ├── storage/          Models, repositories, migrations
│   │   └── pipeline.py       The original V1–V6 enquiry workflow
│   ├── tests/                pytest suite
│   └── scripts/checks/       Manual connectivity checks for external services
├── frontend/                 Next.js web app (React Flow canvas)
└── docs/                     Roadmap summary, architecture, changelog
```

## Quick start

```bash
# API
cd backend
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -e ".[dev]"
copy .env.example .env             # macOS/Linux: cp …; then fill it in
python -m autoflow.api             # http://127.0.0.1:8000 (docs at /docs)

# Web app (second terminal)
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

Run the checks with `pytest` (backend) and with `npm run typecheck && npm run lint && npm run build` (frontend).

**Whole stack in Docker** (PostgreSQL, API, worker, web):

```bash
cp deploy/compose.env.example deploy/compose.env
docker compose up --build          # http://localhost:3000
```

Scheduled workflows need the worker: `python -m autoflow.worker`.

Safety switches (`EMAIL_SEND_ENABLED`, `AI_CLASSIFICATION_ENABLED`) default to `false`. During development, emails are redirected to a test inbox and only fake customer data is used.

## Documentation

- [Product roadmap (summary)](docs/roadmap/README.md)
- [Architecture](docs/architecture.md)
- [Operations runbook](docs/operations.md)
- [Changelog](docs/CHANGELOG.md)
- [Help centre for shop owners](docs/help/README.md)
- [Backend reference](backend/README.md) · [Frontend](frontend/README.md)
