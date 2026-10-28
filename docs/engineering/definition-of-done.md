# Definition of done

A feature or fix is **done** only when every point below is true. A version is released only when all its items are done. The pull-request template repeats this list so nothing is skipped.

## For every change

1. **Implemented:** it does what the roadmap item or issue describes, including the unhappy paths: bad input, a missing connection, the app being down.
2. **Tested:**
   - automated tests cover the behaviour and the main failure cases;
   - the full backend suite passes;
   - the frontend type check, lint and production build are clean.
   - Bugs get a test that failed before the fix.
3. **Permission-checked:** every new API route uses the narrowest role that makes sense (viewer, member, admin, owner or staff). A test shows a lower role is refused, and other workspaces' data is never reachable.
4. **Logged:** security-relevant actions write an audit event, and errors carry a clear, plain-language message. No secrets appear in logs or responses.
5. **Reversible:**
   - database changes come as a migration with a working downgrade, checked with `alembic upgrade head`, `alembic check`, then downgrade and re-upgrade;
   - risky or unfinished features ship behind a feature flag (`luphina/features.py`) that is off by default;
   - actions that change things outside Luphina either can't happen twice or have a defined undo (compensation).
6. **Documented:**
   - the CHANGELOG entry and the help article for anything users see;
   - `docs/operations.md` for anything operators need;
   - `docs/roadmap/status.md` updated;
   - checks that can't run locally added to `docs/deferred-checks.md`.
7. **Translated:** every new interface text exists in all supported languages (English, Spanish, French, German, Turkish).
8. **Accessible:** usable with a keyboard, labelled for screen readers, with readable contrast, and working on a phone.

## Extra for some changes

- **AI prompts or model changes:** run `python evals/run_builder_eval.py`. At least 80% of cases must pass on the first attempt (the MVP gate), and the result must not fall below the previous run. This uses AI credits.
- **Engine, queue, webhooks or billing:** the duplicate-effects test (`tests/test_duplicate_soak.py`) passes. Before a gate review, run it with 1,000 orders and save the report in `docs/evidence/`.
- **New integrations:**
  - credentials stay encrypted, and URLs pass the outbound-network check;
  - the connection health check gets a read-only test;
  - contract tests are added once a vendor sandbox is available.
- **Anything sent to customers:** it goes through approvals and the outbound safety check.

## Item status on the roadmap

`docs/roadmap/status.md` uses these statuses:
- **not started**
- **in progress**
- **done and verified:** every point above is met
- **blocked:** say on what, for example a decision or an account
- **dropped:** say why

Owners are added per item once the team is chosen. "Who builds it" is still an open decision.
