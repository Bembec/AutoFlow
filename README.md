# AutoFlow AI

AutoFlow (working name) lets a small or mid-sized business describe a process in plain words and get a working, AI-powered automation, with no developers needed.

This repository holds the whole product as a monorepo. Today it contains the
**V1–V6 enquiry-automation prototype** (Python). It will grow into the platform
described in the [product roadmap](docs/roadmap/README.md).

## Repository layout

```
AutoFlow/
├── backend/                 Python backend and workflow engine
│   ├── src/autoflow/        Application package
│   │   ├── pipeline.py      Customer-enquiry workflow (entry point)
│   │   ├── config.py        Paths and .env settings
│   │   ├── activity_log.py  Timestamped audit log
│   │   ├── classification/  AI (Gemini) classification
│   │   ├── emails/          Email templates and Gmail sender
│   │   ├── integrations/    Airtable, exchange rates
│   │   └── storage/         SQLite persistence
│   ├── scripts/checks/      Manual connectivity checks for each external service
│   ├── tests/               Automated tests (pytest)
│   ├── data/sample/         Sample (fake) input data
│   ├── data/output/         Generated output (git-ignored)
│   ├── pyproject.toml
│   └── requirements.txt     Pinned dependency versions
├── frontend/                Web app (Next.js), starts at the prototype stage
└── docs/                    Roadmap, architecture and changelog
```

## Quick start (backend)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -e ".[dev]"
copy .env.example .env            # macOS/Linux: cp .env.example .env, then fill it in

python -m autoflow                # run the workflow
pytest                            # run the tests
```

Safety switches in `.env` (`AI_CLASSIFICATION_ENABLED`, `EMAIL_SEND_ENABLED`)
are `false` by default. During development every email is redirected to
`EMAIL_TEST_RECIPIENT`, and only fake customer data is used.

## Documentation

- [Product roadmap](docs/roadmap/README.md)
- [Architecture: current and target](docs/architecture.md)
- [Changelog (V1–V6)](docs/CHANGELOG.md)
