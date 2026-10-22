# Changelog

## Unreleased: repository restructure
- Moved into a monorepo layout (`backend/`, `frontend/`, `docs/`) with an installable `autoflow` package.
- Split `main.py` into a `run()` pipeline and separate modules for Airtable, exchange rates, the activity log and config.
- Generated files now go to `backend/data/output/` and are git-ignored.
- Fixed: the `workflow_runs` table was never created (it ran on a closed connection).
- Removed a duplicate `log_airtable_event` definition.
- `requirements.txt` re-encoded from UTF-16 to UTF-8; added `GEMINI_MODEL` and `AI_CLASSIFICATION_ENABLED` to `.env.example`.
- Added pytest tests.

## V6: Database persistence
SQLite storage, upsert by email, and workflow-run history.

## V5: AI-assisted classification
Gemini classification with reasons, human approval or correction, and a keyword-rule fallback.

## V4: Controlled email automation
Personalized previews, human approval, Gmail test sending, and a safety switch.

## V3: Airtable synchronization
Create/update by email, validation, pagination, and logging.

## V2: API enrichment
EUR→USD reference rate and sample quotes for Sales enquiries.

## V1: CSV processing
Categorize enquiries, write the processed CSV, and log activity.
