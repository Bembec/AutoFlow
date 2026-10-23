# Deferred checks (run in the cloud)

The development PC has very little free memory, so only small, targeted
checks run there. The heavier checks below are deferred.

**Most of them run automatically:** every push to `main` triggers GitHub
Actions (`.github/workflows/ci.yml`), which runs the full backend suite on
SQLite and PostgreSQL, the migration round-trip, the frontend type
check/lint/production build, and both Docker image builds. Check the
**Actions** tab on GitHub.

The items marked **manual** need a person or a bigger machine, such as
GitHub Codespaces, a cloud VM, or any laptop with free memory.

## How to run the manual ones

```bash
# Full stack in Docker (needs ~4 GB free RAM)
cp deploy/compose.env.example deploy/compose.env
docker compose up --build            # open http://localhost:3000

# Or without Docker
cd backend && pytest                 # full backend suite
cd frontend && npm run build         # production build
```

## Open items

| Version | Check | Where | Status |
| --- | --- | --- | --- |
| V24 | Full backend suite and frontend build | CI (automatic) | check the Actions run for V24 |
| V24 | Install on a real phone: open the app in Chrome (Android) or Safari (iPhone) → "Add to Home Screen" → it opens on Approvals; approve one item with a thumb tap | **manual**, phone | to do |
| V24 | Open a notification link `/approvals?focus=<id>` on the phone and check that the right approval is highlighted | **manual**, phone | to do |
| V22 | Run the full AI builder eval: `cd backend && python evals/run_builder_eval.py` (15 cases; uses AI credits) | **manual**, any machine with an AI key | 9 of 15 cases checked so far |
| V20+ | Real Gmail IMAP/SMTP round-trip with an app password (send yourself a PDF invoice; check the run and the sheet row) | **manual**, needs your Gmail | to do |
| V19+ | Real Shopify test store: order paid and checkout webhooks → invoice and reminder flows | **manual**, needs a Shopify dev store | to do |
| V16 | `docker compose up --build` full-stack smoke test | **manual**, Docker machine | to do |
