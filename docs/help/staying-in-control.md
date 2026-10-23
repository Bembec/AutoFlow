# Staying in control

## Approvals

These always wait for a person in **Approvals**:

- **Emails to customers.** You see the full message first.
- **AI results the AI is unsure about.** You can correct the result before the workflow continues.
- **Anything that looks like a trick.** For example, a review or email that tries to give the AI instructions ("ignore your rules…").

To approve *every* action that changes something (saving, sending, posting), turn on **Settings → Safety limits → Approve everything**.

## Notifications

Under **Settings → Notifications**, choose an email address (sent through one of your email connections) and/or a Slack channel (add a **Slack** connection with an incoming-webhook URL). AutoFlow then tells you when something waits for your approval, or when a live run fails. Press **Send a test** to check it works.

## Test runs

**Test run** uses example data and only *pretends* to send or save, so it's safe to press as often as you like.

## Daily limits

Under **Settings → Safety limits** you choose the most runs, AI calls and emails per day. When a limit is reached, AutoFlow stops that step and tells you why. This prevents runaway costs or accidental mass emails.

## Pause or stop

- **Pause** one workflow from its page. Runs in progress are cancelled, and nothing new starts until you resume.
- **Stop all automations** (Settings → Emergency stop) stops everything in your workspace at once, including incoming webhooks.

## When something fails

Open **Run history** and click the run to see each step's input, output and error.

- **Failed:** fix the cause (e.g. reconnect an app), then press **Retry from failed step**. Steps that already worked are not repeated.
- **Needs attention:** AutoFlow is not sure whether a step (like sending an email) happened. Check first, for example in your sent folder, then press **I checked — retry** only if it did not happen.
