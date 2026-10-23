# Resume here

**Read this first when work starts again**, whether it's you, Claude or another developer. It says where the work stopped and exactly where to begin.

- **Last updated:** 2026-10-23
- **Version:** 0.48.1 (V48 plus a data-safety fix)
- **Repository:** github.com/Bembec/AutoFlow (`main`)

## Where we stopped

Work paused at the owner's request after **V48** ("make everything active and interconnected"). Everything up to V48 is committed, pushed and passing:
- backend: 325 tests;
- frontend: type check, lint and production build.

The decisions only you can make are in **[DECISIONS-NEEDED.md](DECISIONS-NEEDED.md)**.

### What is built (V1 to V48)

| Area | What exists |
| --- | --- |
| Core | Accounts, isolated workspaces, roles, two-factor login, activity log, data export and deletion |
| Engine | Draft, test and live runs; versions, compare and rollback; retries; no duplicate actions (proved with 1,000 orders); queue and worker; delays; undo for invoices; "it did happen, continue" |
| Logic | Conditions, comparisons, AND/OR, for-each loops |
| AI | AI builder from plain words; extract, classify, summarise, draft and translate steps; AI assistants (look up, propose, you approve); quality sampling and review; help assistant |
| Integrations | Shopify, WooCommerce, email (SMTP/IMAP), Google Sheets, Airtable, Slack alerts, any REST API, webhooks; MCP tools (client) and AutoFlow as an MCP server; connection health checks |
| Shop features | 36 templates (32 for e-commerce, 3 assistant roles, 1 general), invoices with voiding, abandoned-cart tracking, insights with time and money saved, suggestions |
| Safety | Approvals, emergency stop, daily limits, monthly AI budget, phishing check on outgoing email, new-account limits, abuse reports, staff suspension, prompt-injection guard |
| Business | Plans and billing (Stripe-ready), usage alerts, onboarding checklist, demo workspace |
| Website | Home with live demo, templates, integrations, pricing, security, report abuse; in 5 languages |
| App languages | English, Spanish, French, German, Turkish |

**All features are on by default since V48.** Any of them can be switched off per environment (`AUTOFLOW_FEATURES="name=off"`) or per workspace (staff API). See `docs/operations.md`.

## Where to begin next

### 1. First, no decisions needed: V49 tidy-up pass

- **Make the remaining English-only text in the app translatable.** Some buttons, hints and confirmation pop-ups are still hard-coded English. Search the app screens for literal text:
  - `frontend/src/app/(app)/settings/page.tsx` (most of the cards);
  - `frontend/src/app/(app)/workflows/[id]/page.tsx` (Settings and Trigger panels, confirm dialogs);
  - `frontend/src/app/(app)/connections/page.tsx` (Show tools, form hints);
  - `frontend/src/app/(app)/billing/page.tsx` (usage sentences);
  - `frontend/src/app/(app)/executions/[id]/page.tsx` (delay and approval notes, confirm text);
  - `frontend/src/components/StepEditor.tsx` (labels such as "Step name", "Attempts").

  Add each text to `frontend/src/lib/i18n.tsx` in all five languages; the scratchpad scripts in the worklog show the pattern.
- **Small layout fixes:** indentation inside the Versions list and the old condition editor block in `StepEditor.tsx`.
- **Optional:** a nav item for **AI quality** (today it's reached from Insights).

### 2. Then, needs your input: see DECISIONS-NEEDED.md

Brand, hosting, legal pages, and the Shopify, Gmail and Free-plan choices each unlock a list of work. That file says which.

### 3. Then, needs real-world access: `docs/deferred-checks.md`

Phone install, real stores, real Gmail, real AI key, a real MCP client, a PostgreSQL run of the 1,000-order test, and a native-speaker review of the translations.

## How to run it locally

```bash
# Backend (Python 3.13+), from backend/
.venv/Scripts/python -m pytest -q -p no:logging      # tests (about 3-6 minutes)
.venv/Scripts/python -m autoflow.api                  # API on http://127.0.0.1:8000
.venv/Scripts/python -m autoflow.worker               # background worker (delays, queue)
PYTHONPATH=src .venv/Scripts/python -m autoflow.demo  # demo shop: demo@autoflow.example / demo-password-2026

# Frontend, from frontend/
npm run typecheck && npm run lint && npm run build
# Production preview: copy static files next to the standalone server, then run it
rm -rf .next/standalone/.next/static .next/standalone/public
cp -r .next/static .next/standalone/.next/static && cp -r public .next/standalone/public
cd .next/standalone && PORT=3000 HOSTNAME=127.0.0.1 node server.js   # http://localhost:3000
```

**Low memory on this computer:** run checks one at a time with the preview stopped. Claude Code stops idle background servers when memory runs short. Starting it with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` prevents that.

## Working rules (keep these)

1. Each version: build, then tests, then CHANGELOG, `docs/worklog/2026-10-22.md`, `docs/roadmap/status.md` and `docs/deferred-checks.md`, then commit and push to `main`.
2. Follow `docs/engineering/definition-of-done.md`: tested, permission-checked, logged, reversible, documented, translated, accessible.
3. After editing `docs/help/*.md`, run `python backend/scripts/sync_help.py`; a test fails otherwise.
4. Keep everything country-neutral until the launch country is decided.
5. The repository is public. Never commit `backend/.env`, secrets or the private roadmap `.docx` files; `.gitignore` covers them.
6. TrustLayer and GreyGuard are not linked to AutoFlow. Never mention them.

## Where everything is written down

| File | What it holds |
| --- | --- |
| `docs/CHANGELOG.md` | What each version added (newest first) |
| `docs/worklog/2026-10-22.md` | The detailed session log: every version, decision, problem and fix |
| `docs/roadmap/status.md` | Roadmap items and their status |
| `docs/roadmap/*.docx` | The full private roadmap, v2.0, local only |
| `docs/deferred-checks.md` | Checks that need a phone, real accounts, the cloud or people |
| `docs/operations.md` | Running, deploying, feature flags, staff tools, incidents |
| `docs/help/` | The user help articles; the in-app help assistant answers from these |
| `docs/DECISIONS-NEEDED.md` | Your decisions, and what each one unblocks |
