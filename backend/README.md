# AutoFlow backend

Python package `autoflow`. It currently runs the V1–V6 customer-enquiry workflow:

1. Read enquiries from `data/sample/customers.csv`
2. Classify each one as Sales / Support / Other — Gemini with human review, or keyword rules as a fallback
3. Add a EUR→USD sample quote to Sales enquiries (Frankfurter API)
4. Save results to SQLite (`data/output/autoflow.db`) and CSV
5. Generate email previews; a human approves one test email (Gmail)
6. Sync customers to Airtable (create / update / skip, deduplicated by email)
7. Write the activity log and record the workflow run

## Commands

| Task | Command |
| --- | --- |
| Run the workflow | `python -m autoflow` (or `autoflow`) |
| Start the API server | `python -m autoflow.api`, then open http://127.0.0.1:8000/docs |
| Run the tests | `pytest` |
| Inspect the database | `python -m autoflow.storage.database` |
| Check Airtable access | `python scripts/checks/check_airtable.py` |
| Check the exchange-rate API | `python scripts/checks/check_exchange_rate.py` |
| Check Gemini access | `python scripts/checks/check_gemini.py` |

`scripts/checks/create_airtable_test_record.py` writes one test record to Airtable.

## REST API (V7)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Service status and version |
| GET | `/customers?category=Sales` | Stored customers, optionally filtered |
| GET | `/customers/{id}` | One customer with every field |
| GET | `/workflow-runs?limit=10` | Most recent workflow runs |
| POST | `/workflow-runs` | Run the workflow without a terminal (AI results stay unreviewed, no email is sent) |

## Configuration

All settings live in `backend/.env` (see `.env.example`). Generated files go to
`data/output/`, or to `AUTOFLOW_DATA_DIR` if that variable is set.
