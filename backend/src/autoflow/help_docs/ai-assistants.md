# AI assistants

> AI assistants appear when **AI assistants** is switched on for your workspace. During the early rollout, ask support to switch it on.

An AI assistant handles one job for you, such as reading support emails and flagging orders that need a person. It works in two steps.

## Ready-made roles

Open **AI assistants** in the menu. Each role shows what it can look up and what it can propose. Press **Set up this assistant**, test it with the sample message, then publish it.

- **Support inbox assistant:** reads customer emails, checks the order, drafts a friendly reply and proposes a "needs-human" tag or an order note. You approve the actions and the reply.
- **Order watcher:** looks at each paid order and proposes tags such as "vip", "gift" or "check-address" for your team.
- **Refund request helper:** reads refund requests and proposes voiding the order's invoice, with an order note explaining why.

Once an assistant is set up, the page shows how many messages it handled this week, what's waiting for your approval and anything that needs attention. You can pause or resume it there.

## 1. The assistant thinks and proposes

The **AI assistant** step reads its input (for example an incoming email) and follows the job you describe in plain words. It may:
- **look things up** with read-only tools you choose: checkout status, exchange rates, your shop's API, or a read-only MCP tool;
- **answer** with a short summary and a label;
- **propose actions** from a list you choose: tag or note a Shopify order, update a customer in Airtable, void an invoice, and so on.

It never changes anything itself.

## 2. You approve, then it acts

The **Carry out the proposals** step always waits for your approval. If the assistant proposes nothing, there is nothing to approve and the step is skipped. In **Approvals** you see each proposed action and why the assistant suggests it. Only after you approve does AutoFlow carry them out.

## The guardrails

- **Nothing happens twice:** the assistant can only propose actions that are safe to repeat (tags, notes, upserts, voiding). A retry after a problem never doubles anything.
- **No emails or AI from proposals:** those have their own approvals and limits. Use a normal email step for replies.
- **Fixed accounts:** the connections it uses are set in the workflow. The assistant can't pick another account.
- **Bounded:** at most 5 rounds of thinking per run. Each round counts as one AI call against your daily limit and monthly AI budget.
- **Careful with messages:** the email or message it reads is treated as untrusted. Attempts to manipulate it, and unsure answers (confidence below 0.6), go to a person for review.
- **Only what you allow:** any proposal outside your list is dropped and shown in the run as "rejected".
