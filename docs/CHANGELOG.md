# Changelog

## V48: Everything active, and a resume point
- **All features are on by default:** conditions and loops, MCP tools, AI assistants and AI assistant access (the MCP server) join the others. Each can still be switched off per environment or per workspace. The tests that check "refused while off" now switch the feature off explicitly.
- The help articles no longer say "ask support to switch it on". The website's "Early access" badge is removed.
- **`docs/RESUME-HERE.md`:**
  - where work stopped and what is built;
  - exactly where to begin (the V49 tidy-up list);
  - how to run everything;
  - the working rules.
- **`docs/DECISIONS-NEEDED.md`:** every open decision, with options, the roadmap's recommendation, what it unblocks and where it plugs in.
- The README points to both files.
- Checks:
  - backend: 324 passed;
  - frontend: type check, lint and build all clean.

## V47: Eight more e-commerce templates
- **New templates:**
  - **Cancelled order → void invoice** (Shopify).
  - **Daily order digest:** an evening AI summary from your shop's API.
  - **Big refund alert** (early access): refunds over 100.
  - **Check big first orders** (early access): a first order over 300 is tagged "check-before-shipping" and you get an email.
  - **Reply to reviews in any language:** translated for you, with the reply drafted in the reviewer's language.
  - **Thank loyal customers:** on the third order.
  - **Abandoned checkouts → Airtable**.
  - **Support emails → log sheet:** topic-classified.
- **36 templates in total**, 32 of them for e-commerce. Each new one runs every step on its sample data, and its conditions are tested to skip ordinary cases.
- Every customer email still waits for approval.
- The help article "E-commerce templates" covers them, and the help assistant's copy is re-synced.
- Checks: backend 324 passed. There are no app changes.

## V46: The website in five languages
- **Every page of the public website** is now in English, Spanish, French, German and Turkish:
  - home, including the "type a task" demo;
  - pricing, including plan limits and the FAQ;
  - templates, integrations and security;
  - report abuse;
  - the header and footer.
- **Language picker** in the site header. It shares the app's saved choice, and the browser's language is used otherwise.
- **How it works:**
  - pages are still pre-built in English, for speed and search engines, and switch to the visitor's language on load;
  - `lib/site-i18n.tsx` holds 185 translated sentences keyed by their English text, and pages render `<S t="…" />`;
  - anything not yet translated simply stays English;
  - a coverage check confirms that every visible string has a translation.
- The demo's example chips are shown translated but still pick the right preview.
- Template names and descriptions come from the server and stay English for now.
- A native-speaker review is listed in deferred checks, together with the app texts.
- Checks: frontend type check, lint and build all clean, with pages pre-rendered. No backend changes.

## V45: AI quality checks (production evaluations)
- **Sampling of live AI results:** after a live AI step succeeds (any `ai_*` step or `ai_agent`), a share of results is kept for a person to judge.
  - The default is 5%, adjustable from 0 to 20% by an admin.
  - The choice is deterministic per run and step, so the same step is never sampled twice.
  - It never slows down or blocks a run.
  - Results that already went to human review are skipped.
  - Stored inputs and outputs are trimmed to 4,000 characters.
- **AI quality page** (`/quality`, linked from Insights):
  - the share judged good over 30 days, plus how many are waiting and how many are checked;
  - Waiting and Checked tabs, each sample showing what went in and what the AI produced;
  - **Good** / **Not right** with an optional note;
  - quality per kind of AI step;
  - the sampling-rate setting.
- **API:**
  - `GET /workspaces/{id}/quality` (summary, including the weekly good rate);
  - `GET /quality/samples?status=waiting|reviewed`;
  - `POST /quality/samples/{id}` (members);
  - `PUT /quality/settings` (admins, audited).
- Migration 0018 adds `quality_samples` and `workspaces.quality_sample_percent`.
- 16 new interface texts in all five languages. The help article "Staying in control" is updated.
- Checks:
  - backend: 314 passed;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.

## V44: AutoFlow as an MCP server (behind the `mcp_server` flag)
- **Outside AI assistants** (any MCP client, such as Claude) can run the workflows you opt in and check their runs, at `/mcp` (JSON-RPC over Streamable HTTP; supports initialize, ping, `tools/list` and `tools/call`).
- **Workspace API keys** under Settings → Access for AI assistants:
  - shown once, stored only as a hash;
  - "last used" is displayed;
  - revoke any time, which takes effect immediately;
  - creating and revoking keys is audited.
- **Opt-in per workflow:** "Let AI assistants run this workflow" in the workflow's Settings. Only published, active workflows that are ticked become tools. Their input schema comes from the trigger's sample data.
- **Tools:** `run_<workflow>` per opted-in workflow, plus the read-only `list_recent_runs` and `get_run` (only for opted-in workflows).
- **The usual rules apply:**
  - approvals still wait for a person, and the assistant is told so;
  - limits, the email safety check and audit logging (`mcp.run_workflow` with the key's name) all apply;
  - an optional `idempotency_key` returns the same run instead of starting a second one;
  - each key can start 60 runs an hour;
  - other workspaces' runs are never visible.
- Migration 0017 adds `api_keys` and `workflows.mcp_enabled`. The web app forwards `/mcp` to the API.
- A new help article: "Let other AI assistants use AutoFlow (MCP)".
- Checks:
  - backend: 310 passed, including 6 MCP server tests;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.
- Testing with a real MCP client needs a public address and is listed in deferred checks.

## V43: AI assistants, part 2: ready-made roles
- **AI assistants page** (`/assistants`, a new menu item shown only when `ai_assistants` is on):
  - **Your assistants:** each one shows whether it's live, how many it handled this week, how many are waiting for approval (with a link) and failures, plus Open and Pause/Resume.
  - **Ready-made roles:** each shows what it can look up, what it can propose and what it needs, with **Set up this assistant** (installs the role and opens its test run).
- **Three roles** (templates in category "Assistant"):
  - **Support inbox assistant:** checks the checkout, drafts a reply, and proposes a tag or note; the reply is a normal approved email.
  - **Order watcher:** proposes "vip", "gift" or "check-address" tags.
  - **Refund request helper:** proposes voiding the invoice plus an order note.
- API: `GET /workspaces/{id}/assistants` returns the roles and the active assistants with their 7-day stats.
- Fix: the condition "has a value" now treats an empty list or object as empty. So "no proposals" skips the approval step instead of asking you to approve nothing.
- 17 new interface texts in all five languages. The help article "AI assistants" is updated.
- Phase 2's "AI agents for set roles" item is now done.
- Checks:
  - backend: 304 passed;
  - frontend: type check, lint and build all clean.

## V42: AI assistants, part 1 (behind the `ai_assistants` flag)
- **`ai_agent` step:** an assistant for one job, described in plain words.
  - It reads its input and may call **read-only tools** you choose: checkout status, exchange rates, `http_get`, `mcp_read`.
  - It finishes with an answer, a label and **proposed actions**.
  - It takes at most 5 rounds, and each round counts as an AI call against the daily limit and monthly AI budget.
  - The input and every tool result are fenced as untrusted and scanned for prompt injection.
  - Suspected manipulation and confidence below 0.6 go to review.
- **`agent_execute` step:** carries out the proposals **only after approval**, and it always requires approval.
  - It accepts only actions that are safe to repeat: tags, notes, upserts, void invoice, record order, save customer, log.
  - It never sends email or uses AI.
  - Connections come from the workflow's fixed `defaults`, so the model can't pick another account.
  - Proposals outside the allowed list are dropped and shown as rejected.
- Saving a workflow with assistant steps needs `ai_assistants` switched on. The editor hides the steps otherwise.
- A new help article: "AI assistants".
- Checks:
  - backend: 297 passed, including 7 assistant tests (tool-list invariants, look-up-propose-approve end to end, fixed connections, injection review, bounded rounds, AI limit, feature flag);
  - frontend: type check, lint and build all clean.

## V41: Template library reaches 25
- **Eleven new e-commerce templates:**
  - **Welcome first-time customers:** only for a customer's first order.
  - **Ask for a review a week later:** uses a 7-day wait.
  - **Orders → spreadsheet** and **WooCommerce orders → spreadsheet**.
  - **Customers → Airtable:** adds or updates customers, matched by email.
  - **Tag big orders** (early access): Shopify orders over 150 get the "big-order" tag.
  - **Bad review alert** (early access): for reviews of 2 stars or less.
  - **Payment failed reminder:** a link to pay again on your own shop.
  - **WooCommerce completed: thank you**.
  - **WooCommerce cancelled → void invoice** (early access): uses OR, for cancelled or refunded.
  - **Wholesale lead alert:** AI spots bulk enquiries and emails you a summary.
- **25 templates in total**, meeting the Phase 2 target. Every new one test-runs with its own sample data, with every step actually running, and its conditions are tested to skip the right cases.
- Every email still waits for approval.
- The help article "E-commerce templates" covers all of them, and the help assistant's copy is re-synced.
- Checks: backend 290 passed. There are no app changes, since templates come from the server.

## V40: Help assistant
- A **Help** button on every app page opens a panel for "how do I…?" questions, answered in the user's language.
- **It answers only from the help articles.**
  - The question is matched to the most relevant help sections, with rare words weighted more heavily.
  - The AI writes a short answer from those sections alone, and says so (pointing to support) when they don't cover the question.
  - The answer shows which articles and sections it came from.
  - Without an AI service, the matching help sections are shown instead, so help always works.
- **Free for customers:** questions don't count against the workspace's AI limits or budget. Each workspace can ask up to 30 an hour.
- **Help ships with the server:** `docs/help` is the master copy, packaged into the backend by `scripts/sync_help.py`, and a test fails if they drift.
- `POST /workspaces/{id}/help/ask`, behind the `help_assistant` feature flag (on by default).
- 10 new interface texts in all five languages.
- Checks:
  - backend: 276 passed, including 3 help-assistant tests;
  - frontend: type check, lint and build all clean.

## V39: MCP tools (behind the `mcp_tools` flag)
- **MCP server connections:**
  - a server URL (https and public addresses only);
  - an **allowed tools** list set by an admin (`*` for everything);
  - an optional token, which is encrypted.
- **A small built-in MCP client** (`integrations/mcp.py`): JSON-RPC 2.0 over Streamable HTTP.
  - It handles initialize, then the initialized notification, then `tools/list` (with pages) and `tools/call`.
  - It reads both JSON and server-sent-event replies, keeps the session id, and negotiates the protocol version.
  - Errors are explained in plain words, and busy or unreachable servers are retried.
- **Two workflow steps:**
  - **`mcp_read`** runs only tools the server marks read-only (`readOnlyHint`), so it is safe to run during test runs too;
  - **`mcp_call_tool`** is for tools that change things: it **always** needs approval, and test runs only pretend.

  Results come back as `text` plus optional structured `data`, capped at 50,000 characters and treated as untrusted data.
- **On Connected apps:** **Show tools** lists every tool with read-only or changes-things labels and which ones are allowed. **Check connection** makes sure the allowed tools exist.
- **Feature flag:** both the connection and workflows that use MCP steps are refused unless `mcp_tools` is on. The editor hides MCP steps otherwise. The flag check now covers any feature a workflow needs (`required_features`).
- Connection secrets can now be optional (`optional_secrets` in the catalog).
- A new help article: "Use tools from MCP servers".
- Checks:
  - backend: 273 passed, including 7 MCP tests against a fake server in both reply formats;
  - frontend: type check, lint and build all clean.
- A check against a real MCP server is listed in deferred checks.

## V38: Compare workflow versions
- **What changes when you publish:** a panel under the workflow name, shown whenever a draft is waiting, lists every difference from the live version in plain words:
  - new, removed and changed steps;
  - moved steps;
  - before → after for each setting (name, what it does, each input, conditions, loops, retries, time limit, approval, review threshold);
  - trigger changes.
- **Compare with live** in the Versions tab, for the draft or any older version, including "what rolling back to vN would change".
- API: `GET /workspaces/{id}/workflows/{wid}/compare?before=&after=` (default: live → draft). Steps are matched by id, so an edited step shows as changed, not as removed and added.
- The activity log records what each publish changed: the number of changes and the step ids.
- 20 new interface texts in all five languages. The help article "Getting started" is updated.
- Checks:
  - backend: 266 passed;
  - frontend: type check, lint and build all clean.

## V37: Bigger template library
- **Eight new e-commerce templates**, each tested with its own sample data:
  - **Shipping notification:** emails a tracking link, and skips orders without tracking.
  - **Refund → void invoice:** voids the invoice once, then tells the customer, with no second email for a repeated refund.
  - **Weekly sales summary:** a Monday report from the shop API, summarised by AI.
  - **Low-stock alert** (early access): a daily email only when something is below 5.
  - **Order lines → stock sheet** (early access): one row per product, written exactly once, using a loop.
  - **Big-order thank-you** (early access): only for orders over 150, using a number comparison.
  - **Support inbox assistant:** sorts customer emails and drafts replies for approval.
  - **WooCommerce "we're packing it" note**.
- **Feature-aware templates:** templates that need comparisons or loops carry `"feature": "smarter_logic"`.
  - The app offers them only where the feature is on.
  - Installing one elsewhere is refused.
  - The public gallery labels them "Early access".
- Incoming-email data now includes `from_address`, a bare address for replies.
- In test runs, the `void_invoice` step returns a sample customer email, so follow-up emails test cleanly.
- Get started now recommends shipping notifications (Shopify), the packing note and refunds (WooCommerce), and the support assistant (other platforms).
- The help article "E-commerce templates" covers all of them.
- Checks:
  - backend: 264 passed, including 14 new template tests;
  - frontend: type check, lint and build all clean.

## V36: Smarter logic (behind the `smarter_logic` flag)
- **Comparisons:** "is more than", "is at least", "is less than" and "is at most" understand numbers written as text (`"47.60"`, `"1,200.50"`). A value that isn't a number makes the comparison false, never an error. "Doesn't contain" is added too.
- **AND / OR:** `"when": {"all": [...]}` or `{"any": [...]}`, nestable, with up to 10 conditions per group. The step editor offers a list of conditions with "all of these" or "any of these".
- **Loops:** `"for_each": "{{trigger.line_items}}"` runs a step once per item, with `{{item…}}` and `{{index}}` in its inputs, and the output `{"items": [...], "count": n}`.
  - Progress is saved after every item, so a retry continues where it stopped and never repeats a finished item.
  - An uncertain item can be confirmed, and the loop continues with the next one.
  - Each item retries on its own and has its own idempotency key.
  - Lists are capped at 100 items, and a longer list fails clearly.
  - Email, AI and delay steps can't loop, since they have their own limits and approvals.
  - Billing counts one task per item: `billable_events.quantity`, migration 0016.
- **Feature flag:** saving a workflow that uses these features (including from the AI builder) is refused unless `smarter_logic` is on for the workspace. The editor shows the new controls only then. Workflows that are already saved keep running.
- The canvas describes loops and conditions in words (for example "for each in line_items · if total > 200"). The run timeline shows "Repeated for N items".
- A new help article: "Conditions and loops".
- Follow-up fix after user feedback ("couldn't see the edits"):
  - the Edit tab now opens the first step;
  - each step row shows "Edit ▾" and badges for loops and conditions, with a hint above the list;
  - the demo account now opens straight into the demo shop.
- Checks:
  - backend: 250 passed, including 8 new tests for comparisons, groups, validation, the flag, loops, resume and confirm;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.

## V35: Engineering basics (Phase 1 additions)
- **Definition of done** (`docs/engineering/definition-of-done.md`): implemented, tested, permission-checked, logged, reversible, documented, translated, accessible. It adds extra checks for AI, engine and integration changes, plus the roadmap status set. A GitHub pull-request template repeats the checklist.
- **Feature flags** (`autoflow/features.py`):
  - the order is code default, then `AUTOFLOW_FEATURES` per environment, then staff overrides per workspace (`PUT /staff/workspaces/{id}/features`, audited);
  - members read their flags at `GET /workspaces/{id}/features`;
  - the server enforces them (AI builder, Insights suggestions, connection checks), and the app hides what is off;
  - `smarter_logic` is ready, off by default, for the next version.
- **Seeded demo workspace:** `python -m autoflow.demo` creates "Demo Mug Shop" with eight weeks of history, invoices, savings on Insights and one approval waiting. It can't send anything, and it is created only once.
- **AI builder test set** grows from 15 to 60 cases, all marked synthetic until pilots supply real requests:
  - refunds and voiding;
  - WooCommerce notes and status;
  - tracking notes;
  - schedules;
  - must-not-email cases;
  - more unsupported, vague and prompt-injection requests.

  The runner is now a **release gate**: at least 80% of cases must be correct on the first attempt (`--min-first-time`), as the MVP gate requires. An offline test checks that every case names real actions and triggers.
- Fix: Insights no longer fails when a run is stamped slightly in the future (clock skew).
- Migration 0015 adds `workspaces.feature_flags`.
- Checks:
  - backend: 242 passed;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.
- The full AI eval (60 cases) uses AI credits and is listed in deferred checks.

## V34: Proof of reliability (Phase 1 additions)
- **Duplicate test** (`tests/test_duplicate_soak.py`) runs real shop orders through the order → invoice template in queue mode while forcing:
  - the same webhook twice;
  - store redeliveries;
  - double approvals;
  - a mail-server failure followed by a retry;
  - a worker crash mid-send.

  It counts real effects. **Evidence for the MVP gate:** 1,000 orders and 1,167 runs gave exactly 1,000 invoices, 834 emails and 834 billable events, with **zero duplicate business effects** (`docs/evidence/duplicate-soak.md`). CI runs 60 orders on every push.
- **Compensation:**
  - **void an invoice** from the Invoices page, or with the new `void_invoice` workflow step (e.g. for a refund webhook). The invoice keeps its number, the customer's link shows VOID, and voiding twice is harmless;
  - **"It did happen — continue"** for uncertain steps (`POST /executions/{id}/confirm-done`). The step is recorded as done by a person and is never repeated, alongside the existing "I checked — retry".
- **Connection health:**
  - **Check connection** makes a read-only call (SMTP or IMAP login, Airtable whoami, Shopify shop, WooCommerce orders, a Google token refresh);
  - broken connections alert the owner once;
  - a **Reconnect** button signs in again (OAuth) or asks for the new password or key;
  - network trouble isn't mistaken for bad credentials.
- Migration 0014 adds `invoices.voided_at`, `invoices.void_reason` and `connections.last_checked_at`.
- 11 new interface texts in all five languages. The help article "Staying in control" and `operations.md` are updated.
- Checks:
  - backend: 238 passed;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.

## V33: Trust and safety (Phase 1 additions)
- **Email safety check** on every email step, before approval, in test and live runs:
  - It **blocks** credential phishing: a request for a password or security code plus a link. The step fails and the `outbound.blocked` audit event is logged.
  - It **warns** the approver about link shorteners, raw-IP links, many links or recipients, account threats, and requests for card or bank details. Failed-payment emails stay possible.
- **New-account limits:** lower daily limits (200 runs, 50 AI calls, 20 emails) for a workspace's first 7 days. The dashboard explains them, and staff can lift them early.
- **Abuse reporting:**
  - a public `/report-abuse` page, linked in the site footer and on the Security page;
  - `X-AutoFlow-Workspace` and `X-Report-Abuse` headers on every email sent;
  - rate-limited `POST /abuse-reports`;
  - staff list and close reports.
- **Acceptable use enforced in the product:** staff can suspend a workspace, which stops all automations, and the owner can't resume while suspended. Every staff action is audited.
- **AI cost meter and hard cap:**
  - each plan has a monthly AI budget (`ai_budget_usd_month`, proposals: Free $2, Starter $15, Growth $50, Business $150, Enterprise uncapped);
  - spend is estimated as calls x `AUTOFLOW_AI_COST_PER_CALL_USD`;
  - Plan & usage shows a meter and alerts at 80% and 100%;
  - AI steps pause at the cap while everything else keeps running.
- **Cost on the run timeline:** each run shows its AI calls and estimated cost.
- Migration 0013 adds `abuse_reports`, `workspaces.trusted_at` and `workspaces.staff_suspended_reason`.
- 8 new interface texts in all five languages. The help article "Staying in control" and `operations.md` are updated.
- Checks:
  - backend: 231 passed, including 11 new trust-and-safety tests;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.

## V32: Insights and automation suggestions
- **Insights page** (`/insights`, new menu item):
  - time saved, value saved, live runs and success rate over the last 30 days;
  - an 8-week "time saved per week" chart;
  - a per-workflow table.
- **Value of your time:** admins set what an hour is worth and choose a currency (any 3-letter code; no country is assumed). Savings are then shown as money.
- **Suggestions ("process discovery")** use explainable rules over the workspace's own data, ranked fixes first, then setup, then new automations:
  - a workflow that often fails (at least 20% of 5+ live runs);
  - a workflow set up but never published (after one day);
  - a live webhook that the store has never called;
  - no alerts set up while workflows are live;
  - invoices without business details;
  - the next template that fits the store: order → invoice, abandoned carts (Shopify), review replies, and supplier invoices once email is connected.

  Each suggestion says why it's shown. Templates install in one click, and every text is translated.
- The dashboard shows the top suggestion once a workflow exists.
- Workflows now remember which template they came from (`source_template`). Migration 0012 adds that and the time-value settings.
- API: `GET /workspaces/{id}/insights`, and `PUT /workspaces/{id}/insights/time-value` (admins only).
- 42 new interface texts in all five languages.
- Checks:
  - backend: 220 passed, including 4 new insights tests;
  - migrations: upgrade, `alembic check`, downgrade and re-upgrade all clean;
  - frontend: type check, lint and build all clean.

## V31: Public website pages
- **Shared site layout** (`app/(site)/`) with a sticky header and footer. The mobile menu works without JavaScript.
- **Home page** (`/`):
  - hero with a working **"type a task" demo**: type a task or pick an example to preview the drafted steps, with approval steps marked;
  - "Works with" strip;
  - three-step "how it works";
  - six feature cards;
  - template highlights;
  - security teaser;
  - closing call to action.
- **"Build this for real"** keeps the typed task through sign-up (session storage only). After sign-up the AI builder opens with the task already filled in. Without a task, new accounts go to Get started.
- **Pricing** (`/pricing`) reads the live plan list (`/plans`), so prices always match `plans.json`. It includes a plain-language FAQ: what counts as a task, running out, changing plans, no card needed.
- **Templates** (`/templates`): a gallery from the live template list, grouped by category, with "What it needs".
- **Integrations** (`/integrations`): store, email, data, team alerts, webhooks, REST and AI steps. It describes only what the product does today.
- **Security** (`/security`) covers:
  - workspace isolation;
  - encrypted credentials;
  - export and deletion;
  - approvals, emergency stop and limits;
  - careful AI;
  - two-factor login and scrypt password hashes;
  - roles and the activity log;
  - signed webhooks;
  - no double actions;
  - run records;
  - outbound-call protection.

  No certifications are claimed.
- Page titles follow the pattern "Page · Brand" (a title template in the root layout).
- The site text is in English for now. It will be translated once the brand and launch market are decided.
- Checks: frontend type check, lint and production build clean, with every site page pre-rendered as static and checked for content. No backend changes.

## V30: Guided onboarding
- **Get started page** (`/get-started`). New accounts land here.
  - Pick your platform: Shopify, WooCommerce or somewhere else.
  - It recommends the best first automation and two useful follow-ups.
  - One click installs a template and opens its Run tab, ready for a test with sample data.
- **Getting-started checklist** on the dashboard and the Get started page. Its six steps are:
  1. business details;
  2. email connection;
  3. a template;
  4. a passing test run;
  5. a published workflow;
  6. the store connected (first webhook call or live run).

  It shows a progress bar and highlights the next step with a direct link, including `#business` in Settings and the `?tab=` links on the workflow page. You can hide it, and it remembers that per workspace.
- **Backend:** `GET /workspaces/{id}/onboarding` works out each step from current data, so removing the email connection or pausing the workflow un-ticks it again. It is isolated per workspace.
- The workflow page opens the tab named in `?tab=` (run, edit, versions, trigger or settings).
- 37 new interface texts in all five languages (243 in total). The help article "Getting started" is updated.
- Checks:
  - backend: 216 passed, including 2 new onboarding tests;
  - frontend: type check, lint and production build all clean.

## V29: Design system and in-app polish
- **Swappable brand.** All accent colours come from one `brand-*` palette in `frontend/src/app/globals.css`. Name, wordmark, tagline and theme colour live in `frontend/src/lib/brand.ts`. A shared `Logo` component is used in the app, sign-in and home pages. A rebrand means editing those two files and the two `icon.svg` files.
- **Icons** (lucide-react) in the navigation, empty states, errors, menu and sign-out.
- **Consistent controls.** There is an accessible `Tabs` component (arrow keys, `role="tab"`), used on the workflow page. Checkboxes and radios share the brand colour, selects share one style, and inputs have a disabled look.
- **Plain-language run view.** Each step shows a status icon, a readable name and what the action does. Raw input and output, action names and trigger JSON sit under "Technical details". The trigger shows its simple fields as a readable list, and each run status gets a one-line explanation.
- **Status badges** use plain, translated words, for example "Done", "Needs your check" and "Waiting for approval".
- **Loading skeletons** replace the bare "Loading…" text.
- **Illustrated empty states** with an icon and a next-step button.
- **Plain-language errors.** The server's generic messages and every 5xx error become an actionable sentence in the user's language. Network failures are explained, and validation errors name the field.
- **Accessibility:**
  - "Skip to content" link;
  - `aria-current` on the current page;
  - visible keyboard focus everywhere;
  - reduced-motion support;
  - `aria-pressed` on run filters;
  - a labelled, collapsible mobile menu.
- **Desktop layout:** the sidebar stays in place while you scroll, and content is capped at a readable width.
- 47 new interface texts in all five languages (206 in total).
- Checks: frontend type check, lint and production build all clean. No backend changes.

## V28: Translations finished
- Every page of the web app now uses the translation system: workflows, the new-workflow builder, workflow detail (tabs, publish, pause, run panel), run history and run detail, connected apps, invoices, plan and usage, and all Settings cards.
- 159 interface texts, complete in English, Spanish, French, German and Turkish.
- A small `<T k="…"/>` helper for translated text in JSX. Form labels and hints accept any content.
- Checks: frontend type check, lint and production build clean; no backend changes.

## V27: Two-factor login and audit log
- **Two-factor login** with any authenticator app (TOTP, RFC 6238, implemented with the standard library and checked against the RFC test vector):
  - setup with a key or `otpauth://` link, confirmed with a code;
  - 10 one-time recovery codes, stored only as hashes;
  - codes can't be reused, and ±30 s clock drift is allowed;
  - turning it off needs your password plus a code.

  Sign-in asks for the code when needed (`two_factor_required`), translated in all five languages.
- **Audit log** (`audit_events`, migration 0011) records:
  - sign-ins, including failed ones, with the IP address;
  - two-factor changes;
  - members added, removed or given a new role;
  - connections created, updated or revoked, and webhook secrets set or disabled;
  - workflows published, paused, resumed or archived;
  - emergency stop and resume, policy and notification changes;
  - approvals and rejections;
  - data exports, workspace and account deletion, and billing changes.

  No secrets are logged. Admins see the workspace log (`GET /workspaces/{id}/audit`), and each user sees their own recent sign-ins (`GET /auth/activity`).
- Web app: "Two-factor login" and "Activity log" cards in Settings.
- Checks: backend 214 passed; frontend type check, lint and build clean.

## V26: Interface languages
- Translation system (`frontend/src/lib/i18n.tsx`): one dictionary per language, with missing keys falling back to English, so pages can be translated step by step.
- Languages: English, Spanish, French, German and Turkish. The browser language is detected automatically, and a picker in the menu changes it (remembered per device). The server render uses English, so there is no hydration mismatch.
- Translated: navigation, sign-in and registration, dashboard, and the approvals inbox (the phone screen). Other pages are still in English.
- Every language has all 65 keys. Checks: frontend type check, lint and production build clean; no backend changes.

## V25: WooCommerce support
- **Webhooks:** new `woocommerce` signature scheme (`X-WC-Webhook-Signature`, base64 HMAC-SHA256). WooCommerce's setup ping is answered without starting a run, so WooCommerce keeps the webhook active, and its delivery id is used for de-duplication.
- **Orders:** `create_invoice` now understands WooCommerce orders (billing details, line items, totals, `cart_hash` for order tracking).
- **Template:** "WooCommerce order → invoice". Only paid orders are invoiced, and the email goes out only when the invoice is new, so order updates never re-send it.
- **Same fix for Shopify:** the Shopify order template now also emails only for a new invoice, so a repeated delivery adds no second approval.
- **REST connection:** `woocommerce` (https store URL, consumer key and secret) with `woocommerce_add_order_note` and `woocommerce_set_order_status`. Status changes always need approval, only safe statuses are allowed, and the store address is checked for SSRF on every call.
- Web app: WooCommerce option in the webhook setup. Help guide `docs/help/connect-woocommerce.md`.
- Checks run locally: backend 205 passed; frontend type check, lint and production build clean.

## V24: Mobile approvals (installable web app)
- Web app manifest and icon: add AutoFlow to a phone's home screen and it opens on **Approvals**, like an app (shortcuts to Approvals and Run history). It's a progressive web app, so it needs no app store.
- Approval notifications link straight to the approval (`/approvals?focus=<id>`), which is highlighted and scrolled into view.
- Phone layout: large full-width Approve/Reject buttons and a "N to approve" badge in the header.
- Low-memory policy: only targeted checks ran locally (45 backend tests, frontend type check and lint). Heavier checks are listed in `docs/deferred-checks.md`.

## V23: Owner notifications
- AutoFlow tells the business when something needs them: a step or AI result waiting for approval, or a **live** run that failed or needs attention. Test runs never alert.
- Channels: email through the workspace's own SMTP connection, and/or Slack (new `slack` connection; the webhook URL must be on `hooks.slack.com`).
- Notifications are queued in the same transaction as the event and delivered by the worker, so they never slow down or break a workflow. Each is delivered once, failed sends retry up to 5 times, and the email master switch still applies.
- Settings: email address, mailbox and Slack connections, per-kind toggles, and a "Send a test" button. API: `GET/PATCH /workspaces/{id}/notifications` and `POST …/notifications/test`.
- Migration 0010. 8 new tests; backend suite 196 passed.

## V22: AI quality evals and help centre
- **AI builder eval** (`backend/evals/`): 15 plain-language e-commerce requests, each with checks (expected actions and trigger, admitting unsupported apps, asking about vague requests, never disabling approvals). Run it with `python evals/run_builder_eval.py`; results are saved to `data/output/evals/`. The grading logic has unit tests.
- First live run (Gemini) found a real gap: the builder prompt didn't know the email and document triggers. The prompt now explains every trigger type. The re-run passed the affected cases (email, document, escalation, unsupported app); the injection case was safely refused.
- **Help centre** (`docs/help/`): getting started, connecting Gmail (app passwords, SMTP/IMAP), connecting Shopify (webhooks and Admin token), setting up each e-commerce template, and staying in control.
- Web app: the Trigger tab can set up Shopify-signed webhooks (paste the signing secret) without the API.

## V21: Shopify Admin connector, AI usage accounting, error tracking
- **Shopify connection** (Admin API access token + `shop_domain`). The domain must be `*.myshopify.com`, so the token can't be sent anywhere else. New actions:
  - `shopify_tag_order`: merges tags and keeps existing ones; running it again changes nothing.
  - `shopify_set_order_note`.

  Order ids must be numeric, and the API version is set with `SHOPIFY_API_VERSION` (default 2025-07).
- **AI reading of scans and photos** (uploads and email attachments) now counts toward the daily AI limit. It is recorded in `ai_usage_events` (migration 0009). Uploads over the limit are refused with a clear message; for emails, only the affected attachment is skipped.
- **Optional error tracking:** set `SENTRY_DSN` (and install `sentry-sdk`) to report API and worker errors. No personal data is sent and tracing is off by default.

## V20: Email and document triggers
- **Email trigger:** the worker watches an IMAP mailbox (new `imap` connection type, e.g. Gmail with an app password) and starts one run per new email. Messages are read without being marked, and marked read only after their run exists. The Message-ID is the idempotency key, so no email is processed twice. Trigger data includes the sender, subject, text (HTML-only emails converted), attachments and `attachments_text`.
- **Document trigger and uploads:** `POST /workspaces/{id}/workflows/{wf}/documents` (multipart) starts a run from a PDF, image or text file. Any workflow accepts uploads in test mode; live uploads need a published document-trigger workflow.
- **Document reading** (`autoflow.documents`):
  - the file type is detected from content, not the name;
  - text PDFs are read with pypdf;
  - scanned PDFs and photos are transcribed by AI (Gemini or Claude vision through the router), covering "OCR plus LLM extraction";
  - 10 MB size limit, and text capped at 100k characters.
- New template: **Supplier invoice → spreadsheet** (email trigger → `ai_extract` → Google Sheets row, with low-confidence results reviewed).
- Web app: email and document triggers in the editor, "Test/Run with a file…" upload, trigger explanations, and canvas trigger labels.
- Verified: 14 new tests (PDFs, scans, images, uploads, email parsing, inbox poller with a fake IMAP server), and a Chrome test uploading a file through the UI.

## V19: E-commerce pack (first niche)
- Three ready-made automations, each emailing customers only after approval:
  - **Order → invoice:** a Shopify "order paid" webhook creates a numbered invoice (one per order, even if Shopify sends the order twice), records the order, and emails the invoice link.
  - **Abandoned-cart follow-up:** a checkout webhook waits an hour, checks whether the checkout became an order, then reminds the customer with the recovery link. It never emails when this is unknown (no order tracking), so buyers are never reminded.
  - **Review reply assistant:** AI judges the review's mood and drafts a personal reply (no refunds or discounts promised); the owner approves it before it is sent.
- New actions: `create_invoice` (Shopify or generic orders, exact decimal money), `record_order`, `checkout_status`.
- Invoices: sequential numbers per workspace with a prefix, race-safe allocation, and a public printable page behind an unguessable link (escaped content, `noindex`, no caching). Invoices are listed in the app and included in the workspace export.
- Business profile (name, address, tax ID, invoice prefix) under Settings.
- Templates now carry a category and a "needs to work live" checklist.
- Web app: Invoices page, Business details card, template categories and requirements. `/invoices/*` is forwarded to the API.
- Migration 0008. Verified with backend tests (Shopify-signed webhooks end to end) and a Chrome walkthrough.

## V18: Visual step editor
- Form-based workflow editing in the web app:
  - add steps from the action catalogue, drag to reorder, move up/down, delete;
  - fields generated from each action's input spec, with an "insert data from…" picker (trigger fields and earlier step outputs);
  - an "only run if" condition builder;
  - retry, timeout, approval and AI-review settings;
  - trigger type, cron schedule and sample data.
- The server still validates on save and shows any errors. The JSON editor stays under "Advanced".
- Selecting a step on the canvas opens it in the editor. Editor fields have proper labels (accessibility).
- Instant-navigation validation is limited to public pages (`instant = true` on landing, sign-in, register); signed-in pages load data in the browser by design.
- Verified with a scripted Chrome walkthrough: register, template, add a delay step visually, save, test run, dashboard, approvals and billing, with no browser errors.

## V17: Background execution queue and delays
- Queue mode (`AUTOFLOW_EXECUTION_MODE=queue`): API, webhooks and schedules only queue runs, and workers execute them. Inline mode stays the default.
- Atomic claims (no execution runs twice), heartbeats, and recovery of runs from a dead worker. An uncertain side effect still becomes `needs_attention`.
- `delay` action (minutes/hours/days, max 30 days): the execution parks as queued with `run_after` and resumes in a worker. Test runs skip delays.
- Retry backoff is capped at 5 minutes so heartbeats stay fresh. Approvals and retries go back to the queue in queue mode.
- Web app shows waiting steps, delay badges and the resume time. Docker compose runs in queue mode.
- Migration 0007 (run_after, claimed_by, heartbeat_at).

## V16: Operations and production readiness
- Environments: `AUTOFLOW_ENV` is development, staging or production. Outside development, startup fails unless secret keys, PostgreSQL and an https public URL are set; production also requires no email test redirect.
- In staging and production, migrations run as a deploy step (no automatic migration). `/ready` reports database reachability and schema currency, and API docs are hidden in production.
- HTTP middleware: request IDs and access logs, security headers (HSTS outside development), a sign-in rate limit (10/min per IP), and optional CORS.
- Background worker (`python -m autoflow.worker`): cron-scheduled workflows with idempotent slots, honouring the emergency stop and pause, plus token housekeeping. Cron expressions are validated.
- Data ownership: workspace export (no secrets), workspace deletion with name confirmation, and account deletion that protects shared workspaces. New endpoints change member roles and remove members, and the last owner is protected.
- PostgreSQL support (psycopg 3). An empty `DATABASE_URL` means the SQLite default.
- Docker images for the API/worker and the web app (non-root, Next.js standalone), plus docker-compose (PostgreSQL, migrate, API, worker, web).
- GitHub Actions CI: backend tests on SQLite and PostgreSQL, a migration round-trip and `alembic check`, frontend type check/lint/build, and image builds.
- Operations runbook (`docs/operations.md`): deploy, rollback, monitoring, backups and restore tests, key rotation, incident response, data requests.

## V15: Billing and usage
- Plans (Free, Starter, Growth, Business, Enterprise) from a JSON config, with limits on included tasks, workflows and seats.
- Usage metering on the roadmap's billable-task definition. Events are unique per step run (no double billing) and recorded in the same commit as the step's success. Rules-only classification is not billed.
- Plan enforcement:
  - a hard cap on billable steps (optional on paid plans);
  - workflow and seat limits;
  - alerts at 80% and 100%, for projected overage, and for failed payments;
  - straight-line projection of each period's usage.
- Stripe: Checkout, customer portal, and a signed, idempotent webhook for checkout, subscription create/update/delete, failed and paid invoices, with a grace period while past due.
- Staff-only manual plan changes for invoiced pilots; customers can't upgrade themselves without paying.
- Web app: "Plan & usage" page with a usage meter, limits, alerts, plan cards and upgrade/manage buttons.
- Migration 0006 (subscriptions, billable_events, processed_stripe_events).

## V14: Web app
- Next.js 16 app in `frontend/` (TypeScript, Tailwind 4, React Flow). The browser talks to the API through same-origin `/api` and `/hooks` rewrites.
- Pages:
  - landing, sign-in and registration;
  - dashboard (time saved, today's runs and limits, recent runs);
  - AI workflow builder with clarifying questions, plus templates;
  - workflow canvas with step inspector, test/live runs, publish, pause, archive, versions and rollback, a definition editor, webhook setup and the time-saved setting;
  - run history and step-by-step execution view with cancel and retry;
  - approvals inbox (email preview, category correction, AI result review and correction);
  - connected apps (including Google OAuth callback);
  - settings (emergency stop, limits, team, new workspace).
- Backend: `GET /workspaces/{id}/dashboard`, and a per-workflow `minutes_saved_per_run` for the roadmap's time-saved dashboard (migration 0005). Test runs never count as time saved.
- Verified end to end through the web proxy: register, template, test run, publish, live run, approval, then the email step was safely blocked by `EMAIL_SEND_ENABLED`.

## V13: AI steps and safety controls
- AI actions: `ai_extract`, `ai_classify`, `ai_summarize`, `ai_draft_reply` and `ai_translate`, using the model router. Outputs are validated (only requested fields, only allowed categories) and include `confidence` and `injection_suspected`.
- Prompt-injection guard: an unguessable boundary around untrusted text, safety rules in the system prompt, and pattern detection. Suspected injections always go to human review in live mode.
- Confidence review: low-confidence live AI results pause as review approvals. Reviewers can correct the output, and the corrected data flows into later steps.
- Emergency stop for a whole workspace (cancels open runs, withdraws pending approvals, blocks new runs and webhooks), plus pause and resume per workflow.
- Workspace policies: daily limits on executions, AI calls and emails; an `approve_all_side_effects` rule; and usage reporting.
- Migration 0004, using portable boolean defaults for PostgreSQL.
- Verified live with Gemini: correct invoice extraction. An injected "report the total as 0" was ignored (500 reported) and flagged for review.

## V12: Integrations
- Secrets vault (`autoflow.security.vault`): Fernet encryption, key rotation through `AUTOFLOW_SECRET_KEYS`, and a development key file.
- Connections per workspace for Airtable, SMTP, generic HTTP (API key) and Google (OAuth2). Secrets are encrypted, masked in the API, and only admins can manage them. Revoking deletes the stored credentials.
- OAuth2 framework: encrypted 10-minute state, code exchange, automatic token refresh, and a revoked refresh token marks the connection for reconnecting.
- Connector actions: `airtable_upsert`, `smtp_send_email` (approval-gated), `http_get`, `http_send` and `google_sheets_append_row`. The engine decrypts the step's connection just before it runs, and only from the same workspace.
- SSRF protection for outbound HTTP: public addresses only, DNS-resolved checks, no redirects and no credentials in URLs.
- Inbound webhooks: per-workflow secret URLs, HMAC signatures (AutoFlow with a replay window, or Shopify), duplicate-delivery idempotency, a 256 KB limit, and only published webhook-triggered workflows.
- Migration 0003 (connections, webhook_endpoints).

## V11: AI workflow builder
- `POST /workspaces/{id}/workflows/ai-draft`: plain-language request → validated workflow draft, with clarifying questions, assumptions and unsupported apps; optional save as a draft workflow.
- The AI sees the live action catalogue and an example. Its output passes the standard validator, with up to 2 repair rounds that feed the validator's errors back.
- Model router (`autoflow.ai.providers`): Gemini and Claude (`claude-opus-5-5`, server-side refusal fallbacks) with ordered fallback when a provider fails.
- Tests can no longer pick up real credentials from `backend/.env`.
- Verified live with Gemini: a five-step enquiry workflow was drafted valid on the first attempt.

## V10: Workflow engine
- Workflows are defined as data: a trigger, ordered steps, `{{ }}` references to the trigger and earlier outputs, and `when` conditions for branching.
- Action registry with input/output specs and safety flags (side effect, idempotent, requires approval). The existing capabilities became actions: classify, quote, compose, send, save customer and log.
- Strict definition validation; mandatory approvals cannot be switched off.
- Versioning: draft, publish, new draft on edit, and rollback to any version. Workflows can be archived.
- Test mode (side effects simulated) vs live mode (published version only).
- Executor:
  - retries with exponential backoff, per-step timeouts, and non-retryable input errors;
  - resumes from the failed step and never repeats succeeded steps;
  - uncertain non-idempotent side effects become `needs_attention` instead of being retried blindly;
  - honours the `Idempotency-Key` header, and supports cancel and approval-gated steps.
- Built-in template: customer enquiry triage.
- New tables: workflows, workflow_versions, workflow_executions and step_executions. Approvals can now gate an execution step.
- SQLite runs in WAL mode (commits about 30× faster); added a constraint naming convention for future migrations.

## V9: Core foundation (accounts, workspaces, tenant isolation)
- Moved storage to SQLAlchemy 2 with Alembic migrations. SQLite is the default and PostgreSQL is set via `DATABASE_URL`. Migrations run automatically on start.
- New tables: users, workspaces, memberships (roles: viewer, member, admin, owner) and access tokens.
- Customers, workflow runs and approvals now belong to a workspace. Every query is scoped to it, and the same customer email can exist in different workspaces.
- Auth: register (creates an owned workspace), login (bearer token, stored only as a hash), logout (revocation) and token expiry. Passwords are hashed with scrypt.
- API reorganized into routers; all data routes live under `/workspaces/{id}/…` with role checks. Unknown or foreign workspaces return 404.
- Approvals record which user decided them.
- The CLI runs in a "local" workspace. Only that workspace writes local files or uses the `.env` Airtable account, so one tenant's data never reaches another's CRM.
- Tests cover isolation, roles, token expiry and revocation, and run the real migrations.

## V8: Approvals as data
- New `approvals` table and approval service (`autoflow.approvals`).
- Runs without a terminal queue AI classifications and emails as pending approvals.
- API: list, view, approve (with optional category correction) and reject approvals.
- Safety: decisions are atomic and final, emails are blocked until the customer's classification is reviewed, and a correction regenerates the pending email.
- Approval decisions are written to the activity log.
- Added `.gitattributes` to normalize line endings.

## V7: REST API
- FastAPI application (`autoflow.api`) with interactive docs at `/docs`.
- Endpoints for health, customers (with category filter), customer detail, and listing and starting workflow runs.
- The pipeline can run without a terminal (`run(interactive=False)`) and returns a run summary.
- `AUTOFLOW_INPUT_CSV` setting; API host/port settings.

## Repository restructure
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
