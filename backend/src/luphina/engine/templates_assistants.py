"""
Ready-made AI assistant roles (V43), shown on the Assistants page.

Each role is a template whose core is an `ai_agent` step (look things up,
propose actions) followed by `agent_execute` (carry out the proposals after
approval). Emails stay ordinary email steps, so they keep their own
approval and safety checks.
"""

from luphina.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER

FEATURE = "ai_assistants"
CATEGORY = "Assistant"

SAMPLE_SUPPORT_EMAIL = {
    "from": "Grace Hopper <grace@example.com>",
    "from_address": "grace@example.com",
    "to": "support@your-shop.example",
    "subject": "Where is my order #1001?",
    "date": "Thu, 22 Oct 2026 10:15:00 +0000",
    "message_id": "<demo-support-2@example.com>",
    "text": "Hi, I ordered a mug last week (order #1001, checkout chk_8f2c1a) and haven't heard anything. Has it shipped?",
    "attachments": [],
    "attachments_text": "",
}

SAMPLE_REFUND_EMAIL = {
    **SAMPLE_SUPPORT_EMAIL,
    "subject": "Refund for order 820982911946154508",
    "message_id": "<demo-refund-1@example.com>",
    "text": "The mug from order 820982911946154508 arrived broken. I've been refunded by the shop app; please cancel the invoice.",
}

SHOPIFY_DEFAULTS = {
    "shopify_set_order_note": {"connection": "store"},
    "shopify_tag_order": {"connection": "store"},
}


def _execute(allowed, defaults):
    return {
        "id": "act",
        "name": "Carry out the proposals (needs approval)",
        "action": "agent_execute",
        "when": {"left": "{{steps.assistant.output.proposals}}", "op": "exists"},
        "inputs": {"proposals": "{{steps.assistant.output.proposals}}", "allowed": allowed, "defaults": defaults},
    }


SUPPORT_AGENT = {
    "slug": "assistant-support-inbox",
    "name": "Support inbox assistant",
    "category": CATEGORY,
    "feature": FEATURE,
    "requires": [
        "An incoming email connection named \"support-inbox\"",
        "A Shopify connection named \"store\" and an email connection named \"mailbox\"",
        "An AI provider configured on the server",
    ],
    "description": (
        "Reads each customer email, checks the order, drafts a helpful reply and proposes a note or tag on "
        "the order for your team. You approve the actions and the reply."
    ),
    "definition": {
        "trigger": {"type": "email", "connection": "support-inbox", "sample_payload": SAMPLE_SUPPORT_EMAIL},
        "steps": [
            {
                "id": "assistant",
                "name": "Support assistant",
                "action": "ai_agent",
                "inputs": {
                    "instructions": (
                        "You handle customer emails for an online shop. Work out what the customer needs. If they "
                        "give a checkout token, check its status. Write a short, friendly reply to the customer as "
                        "your answer; never promise refunds, discounts or dates. If a person must follow up, "
                        "propose tagging the order 'needs-human' and a short order note saying why."
                    ),
                    "input": "Subject: {{trigger.subject}}\n\n{{trigger.text}}",
                    "tools": ["checkout_status"],
                    "can_propose": ["shopify_tag_order", "shopify_set_order_note"],
                    "defaults": SHOPIFY_DEFAULTS,
                },
            },
            _execute(["shopify_tag_order", "shopify_set_order_note"], SHOPIFY_DEFAULTS),
            {
                "id": "reply",
                "name": "Send the reply (needs approval)",
                "action": "smtp_send_email",
                "when": {"left": "{{steps.assistant.output.answer}}", "op": "exists"},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.from_address}}",
                    "subject": "Re: {{trigger.subject}}",
                    "body": "{{steps.assistant.output.answer}}",
                },
            },
        ],
    },
}

ORDER_WATCHER = {
    "slug": "assistant-order-watcher",
    "name": "Order watcher",
    "category": CATEGORY,
    "feature": FEATURE,
    "requires": [
        "A webhook from your store's \"order paid\" event",
        "A Shopify connection named \"store\"",
        "An AI provider configured on the server",
    ],
    "description": (
        "Looks at every new order and proposes tags for your team: \"vip\" for big or repeat customers, "
        "\"gift\" for gift messages, \"check-address\" when the address looks incomplete. You approve them."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_SHOPIFY_ORDER, "note": "It's a birthday gift!"}},
        "steps": [
            {
                "id": "assistant",
                "name": "Order watcher",
                "action": "ai_agent",
                "inputs": {
                    "instructions": (
                        "Review this paid order. Propose Shopify tags only when clearly justified: 'vip' for orders "
                        "over 150 or customers with many orders, 'gift' when the note mentions a gift, "
                        "'check-address' when the shipping address looks incomplete. Summarise your reasons in "
                        "one sentence as your answer. Propose nothing for an ordinary order."
                    ),
                    "input": "{{trigger}}",
                    "can_propose": ["shopify_tag_order"],
                    "defaults": SHOPIFY_DEFAULTS,
                    "max_rounds": 2,
                },
            },
            _execute(["shopify_tag_order"], SHOPIFY_DEFAULTS),
        ],
    },
}

REFUND_HELPER = {
    "slug": "assistant-refund-helper",
    "name": "Refund request helper",
    "category": CATEGORY,
    "feature": FEATURE,
    "requires": [
        "An incoming email connection named \"support-inbox\"",
        "A Shopify connection named \"store\"",
        "The \"Order → invoice\" workflow (it made the invoices)",
        "An AI provider configured on the server",
    ],
    "description": (
        "Reads refund requests, finds the order and proposes voiding its invoice with an order note "
        "explaining why. Nothing changes until you approve."
    ),
    "definition": {
        "trigger": {"type": "email", "connection": "support-inbox", "sample_payload": SAMPLE_REFUND_EMAIL},
        "steps": [
            {
                "id": "assistant",
                "name": "Refund helper",
                "action": "ai_agent",
                "inputs": {
                    "instructions": (
                        "Decide whether this email is a refund or cancellation request for a specific order. If it "
                        "is and the order id is clear, propose voiding that order's invoice (order_ref = the order "
                        "id) and a short order note saying why. If anything is unclear, propose nothing and say "
                        "what is missing in your answer."
                    ),
                    "input": "Subject: {{trigger.subject}}\n\n{{trigger.text}}",
                    "can_propose": ["void_invoice", "shopify_set_order_note"],
                    "defaults": {"shopify_set_order_note": {"connection": "store"}},
                    "max_rounds": 2,
                },
            },
            _execute(["void_invoice", "shopify_set_order_note"], {"shopify_set_order_note": {"connection": "store"}}),
        ],
    },
}

ASSISTANT_TEMPLATES = (SUPPORT_AGENT, ORDER_WATCHER, REFUND_HELPER)


def role_summary(template):
    """What a role can look up and propose, read from its assistant step."""
    step = next((s for s in template["definition"]["steps"] if s["action"] == "ai_agent"), {})
    inputs = step.get("inputs", {})
    return {"looks_up": list(inputs.get("tools") or []), "proposes": list(inputs.get("can_propose") or [])}
