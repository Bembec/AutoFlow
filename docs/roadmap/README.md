# Product roadmap

Progress against this plan: [status.md](status.md).

This is a public summary. The full plan (`Luphina-Full-Product-Roadmap.docx`, version 2.0 of 23 October 2026, which merges the Roadmap Review and Addendum) is private: keep it locally in this folder, where git ignores it. Version 1 is kept beside it as `Luphina-Full-Product-Roadmap-v1-2026-10-09.docx`.

## Summary

- **Vision:** every business runs its repetitive work on autopilot.
- **Phases (24 months, gated):** MVP at month 4 → paid launch at month 8 → scale by month 15 → enterprise and marketplace by month 24.
- **First niche:** e-commerce stores, with three automations perfected first.

## Build order

1. **Clickable prototype:** type a task, see the workflow on a canvas, test-run it, view run history (sample data).
2. **Core foundation:** accounts, isolated workspaces per business, the database, and a workflow engine with retries and no duplicate actions.
3. **AI builder:** plain words → workflow steps the engine can run.
4. **First integrations:** e.g. Gmail, Google Sheets, Shopify, plus webhooks.
5. **AI steps and approvals:** reading emails and documents, with approval before any sensitive action.
6. **Dashboard and billing:** ready for paid pilots.

## MVP must-haves

- AI workflow builder (chat + canvas)
- Reliable execution engine (retries, timeouts, idempotency)
- 3–5 integrations + webhooks
- Three working automations
- Secure accounts and tenant isolation
- Draft / test / publish modes
- Run history, error handling and approval steps
- Dashboard and basic billing

## Phase 1 additions (October 2026 review)

- **Platform requirements:** Google verification for restricted Gmail scopes, Shopify App Store rules, WhatsApp Business verification, Microsoft publisher verification.
- **Trust and safety:**
  - sending limits;
  - new-account restrictions;
  - outbound content checks;
  - an abuse-report channel;
  - the acceptable-use policy enforced in the product;
  - email only from the customer's own mailbox or verified domain.
- **AI controls:**
  - published AI-provider data terms;
  - pinned model versions with a 200-request test set before changes;
  - a per-workspace AI cost meter and hard cap;
  - labels on AI-generated messages where the law requires them;
  - all data treated as untrusted input.
- **Engineering discipline:**
  - a definition of done;
  - item status with owners;
  - a full test strategy, including connector contract tests;
  - staging and production environments, a demo workspace and feature flags;
  - recovery targets;
  - compensation (undo) for actions that can't be exactly-once.
- **Product details:**
  - test mode;
  - a run timeline including cost;
  - connection health with one-click reconnect;
  - WCAG 2.2 AA accessibility and plain-language errors in acceptance.

## Later phases (additions)

- **Phase 2:**
  - version diff;
  - usage alerts and projected bills;
  - a status page and on-call;
  - a documentation-only AI help assistant;
  - measured case studies;
  - MCP client support;
  - a native mobile app replaced by mobile web plus email, Slack and WhatsApp approvals;
  - AI agents moved to the end of Phase 2 or Phase 3.
- **Phase 3:**
  - workflows exposed as an MCP server;
  - production evaluations;
  - tested industry template packs;
  - partner terms;
  - SOC 2 Type I;
  - data residency if asked.
- **Phase 4:**
  - SSO and SCIM;
  - customer-managed keys if demanded;
  - marketplace review and revenue terms;
  - white-label brand isolation;
  - regional hosting.

## Phase gates

Each gate needs the business condition **and** the product and safety evidence.

| Gate | Business condition | Product and safety evidence |
| --- | --- | --- |
| MVP ready | 3 automations, paid pilots | End-to-end tests pass for the three automations; zero duplicate business effects in 1,000 test runs; tenant-isolation tests pass; restore tested; AI test set ≥ 80% correct first time |
| Product fit | 100 paying, $10k MRR | Workflow success rate ≥ 97% measured; gross margin per plan known; support response target met; platform verifications complete |
| Scale proven | $50k MRR, churn under 3% | Penetration test closed; incident process exercised; SOC 2 Type I evidence underway; connector break rate tracked; on-call in place |

## Open decisions

- Final brand name
- Launch country
- First niche and its 3 automations
- Who builds it
- Build vs. buy integrations
- Funding route
- Positioning (vertical depth, reliability guarantee, done-for-you, or local market)
- Shopify route (App Store app with Shopify billing, or independent platform)
- Gmail access (fund Google's security assessment, narrower scopes, or other providers)
- Free plan (keep, limit AI steps, or replace with a trial)
