## What and why

<!-- One or two sentences, and the roadmap item or issue it closes. -->

## Definition of done ([full text](../docs/engineering/definition-of-done.md))

- [ ] Implemented, including failure cases
- [ ] Tests added; backend suite, frontend type check, lint and build pass
- [ ] Permissions: narrowest role, a lower role is refused, no cross-workspace access
- [ ] Audit events for security-relevant actions; plain-language errors; no secrets in logs
- [ ] Reversible: migration with downgrade (`alembic check` clean); unfinished work behind a feature flag; outside actions can't happen twice or can be undone
- [ ] Docs: CHANGELOG, help article, operations, roadmap status, deferred checks
- [ ] New interface texts in all five languages
- [ ] Keyboard, screen reader and phone checked

## Extra checks (if relevant)

- [ ] AI prompt or model change: `evals/run_builder_eval.py`, first-time pass rate ≥ 80% and not lower than before
- [ ] Engine, queue, webhooks or billing: `tests/test_duplicate_soak.py` passes
- [ ] Customer-facing sending: goes through approvals and the outbound safety check
