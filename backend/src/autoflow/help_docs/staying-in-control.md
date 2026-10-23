# Staying in control

## Approvals

These always wait for a person in **Approvals**:

- **Emails to customers.** You see the full message first.
- **AI results the AI is unsure about.** You can correct the result before the workflow continues.
- **Anything that looks like a trick.** For example, a review or email that tries to give the AI instructions ("ignore your rules…").

To approve *every* action that changes something (saving, sending, posting), turn on **Settings → Safety limits → Approve everything**.

## Notifications

Under **Settings → Notifications**, choose an email address (sent through one of your email connections) and/or a Slack channel (add a **Slack** connection with an incoming-webhook URL). AutoFlow then tells you when something waits for your approval, or when a live run fails. Press **Send a test** to check it works.

## Two-factor login

Under **Settings → Two-factor login**, add AutoFlow to an authenticator app (Google Authenticator, Authy, 1Password…). After that, signing in also asks for the 6-digit code. Keep the 10 recovery codes somewhere safe; each one works once if you lose your phone. **Recent sign-ins** shows where your account was used.

## Activity log

Admins see **Settings → Activity log**: who added people, connected apps, published workflows, approved emails, exported data, and more.

## Test runs

**Test run** uses example data and only *pretends* to send or save, so it's safe to press as often as you like.

## Daily limits

Under **Settings → Safety limits** you choose the most runs, AI calls and emails per day. When a limit is reached, AutoFlow stops that step and tells you why. This prevents runaway costs or accidental mass emails.

New accounts start with lower daily limits for their first week: 200 runs, 50 AI calls and 20 emails. This stops brand-new accounts being misused for spam. Contact support if you need them lifted sooner.

## Email safety check

Every email a workflow sends is checked before it can be approved:
- An email that asks for a password or security code and contains a link looks like phishing. It is **blocked** and can't be sent.
- Other warning signs are **shown to the approver**: link shorteners, links to raw IP addresses, many links or recipients, threats to close an account, or requests for card details.

Emails also carry a header so recipients can report abuse to us.

## AI budget

Each plan includes a monthly AI budget, estimated from the number of AI calls. **Plan & usage** shows how much is used. When it runs out, AI steps pause until the next period; everything else keeps running. Each run's page also shows how many AI calls it made and roughly what they cost.

## Pause or stop

- **Pause** one workflow from its page. Runs in progress are cancelled, and nothing new starts until you resume.
- **Stop all automations** (Settings → Emergency stop) stops everything in your workspace at once, including incoming webhooks.

## When something fails

Open **Run history** and click the run to see each step's input, output and error.

- **Failed:** fix the cause (e.g. reconnect an app), then press **Retry from failed step**. Steps that already worked are not repeated.
- **Needs attention:** AutoFlow is not sure whether a step (like sending an email) happened. Check first, for example in your sent folder. Then choose:
  - **I checked — retry** if it did **not** happen. The step runs again.
  - **It did happen — continue** if it did. The step is recorded as done by you, and the workflow carries on without repeating it.

## Undoing an invoice

Refunded or cancelled orders shouldn't leave an invoice standing. On **Invoices**, press **Void** and give a reason. The invoice keeps its number, so your numbering has no gaps, and the customer's link shows **VOID**. Workflows can do the same with the **void invoice** step, for example when your store sends a refund webhook. Voiding twice changes nothing.

## Connected apps health

On **Connected apps**, **Check connection** makes a harmless read-only call to the app (for example, logging in to your mail server) and tells you whether it works. If an app stops working, during a check or a run, you get an alert and a **Reconnect** button appears: sign in again, or enter the new password or key.
