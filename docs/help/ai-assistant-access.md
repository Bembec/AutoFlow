# Let other AI assistants use AutoFlow (MCP)

If you already use an AI assistant that supports MCP (for example Claude), it can run your AutoFlow workflows for you ("tag order 1001 as VIP") and tell you how runs went.

## Set it up

1. **Settings → Access for AI assistants:** give the key a name, for example "My Claude", and press **Create key**. Copy the key straight away; it's shown only once.
2. In your AI assistant, add an MCP server with the **server address** shown on the card, and the key as a Bearer token.
3. On each workflow you want to offer, open **Settings** and tick **Let AI assistants run this workflow**. Only live (published) workflows that you ticked are offered.

## What the assistant can do

- **Run a ticked workflow**, giving it the same data the workflow's trigger expects.
- **List recent runs** and **look at one run**, only for the workflows you ticked.

## Your rules still apply

- Steps that need approval, such as emails to customers, **wait for you** as usual. The assistant is told that a person must approve.
- Daily limits, the email safety check and the activity log all apply. Every run started this way is logged with the key's name.
- **No double runs:** if the assistant sends an `idempotency_key`, asking twice gives back the same run.
- Each key can start at most 60 runs an hour.
- **Revoke** a key at any time. It stops working immediately.
