"""
E-commerce template pack (the first niche): order → invoice,
abandoned-cart follow-up and review replies.

Every customer email waits for the owner's approval.
"""

# Realistic example of a Shopify order webhook (fake data)
SAMPLE_SHOPIFY_ORDER = {
    "id": 820982911946154508,
    "name": "#1001",
    "email": "ada@example.com",
    "currency": "EUR",
    "subtotal_price": "40.00",
    "total_tax": "7.60",
    "total_price": "47.60",
    "checkout_token": "chk_8f2c1a",
    "customer": {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"},
    "line_items": [
        {"title": "Ceramic mug", "quantity": 2, "price": "12.00"},
        {"title": "Coffee beans 250 g", "quantity": 1, "price": "16.00"},
    ],
}

# Example of a Shopify checkout webhook (fake data)
SAMPLE_SHOPIFY_CHECKOUT = {
    "token": "chk_51b7e0",
    "email": "grace@example.com",
    "currency": "EUR",
    "total_price": "29.00",
    "abandoned_checkout_url": "https://shop.example/checkouts/chk_51b7e0/recover",
    "customer": {"first_name": "Grace", "email": "grace@example.com"},
    "line_items": [{"title": "Linen tote bag", "quantity": 1, "price": "29.00"}],
}

# What a review app sends (fake data)
SAMPLE_REVIEW = {
    "rating": 2,
    "title": "Arrived late",
    "body": "The mug is nice but delivery took two weeks and nobody answered my email.",
    "reviewer_name": "Alan",
    "reviewer_email": "alan@example.com",
    "product_title": "Ceramic mug",
}

ORDER_TO_INVOICE = {
    "slug": "shopify-order-to-invoice",
    "name": "Order → invoice",
    "category": "E-commerce",
    "requires": [
        "A webhook from your store's \"order paid\" event (Shopify: Settings → Notifications → Webhooks)",
        "An email connection named \"mailbox\"",
        "Your business details in Settings (printed on invoices)",
    ],
    "description": (
        "When an order is paid, create a numbered invoice and email the customer a link to it "
        "(after your approval). Also records the order so cart reminders skip buyers."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_ORDER},
        "steps": [
            {
                "id": "invoice",
                "name": "Create the invoice",
                "action": "create_invoice",
                "inputs": {"order": "{{trigger}}"},
            },
            {
                "id": "track",
                "name": "Record the order",
                "action": "record_order",
                "inputs": {"checkout_token": "{{trigger.checkout_token}}", "email": "{{trigger.email}}"},
            },
            {
                "id": "send",
                "name": "Email the invoice (needs approval)",
                "action": "smtp_send_email",
                "when": {"left": "{{steps.invoice.output.customer_email}}", "op": "exists"},
                "retry": {"max_attempts": 2, "backoff_seconds": 5},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{steps.invoice.output.customer_email}}",
                    "subject": "Your invoice {{steps.invoice.output.invoice_number}} for order {{trigger.name}}",
                    "body": (
                        "Hi {{trigger.customer.first_name}},\n\n"
                        "Thank you for your order {{trigger.name}}. Your invoice "
                        "{{steps.invoice.output.invoice_number}} for {{steps.invoice.output.total}} "
                        "{{steps.invoice.output.currency}} is here:\n{{steps.invoice.output.url}}\n\n"
                        "Kind regards"
                    ),
                },
            },
        ],
    },
}

ABANDONED_CART = {
    "slug": "abandoned-cart-follow-up",
    "name": "Abandoned-cart follow-up",
    "category": "E-commerce",
    "requires": [
        "A webhook from your store's \"checkout created\" event",
        "The \"Order → invoice\" workflow running (it tells this one who already bought)",
        "An email connection named \"mailbox\"",
        "The background worker (for the 1-hour wait)",
    ],
    "description": (
        "When a checkout starts, wait an hour. If it did not become an order, send a friendly "
        "reminder with the cart link (after your approval). Never emails people who bought."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_CHECKOUT},
        "steps": [
            {"id": "wait", "name": "Wait an hour", "action": "delay", "inputs": {"hours": 1}},
            {
                "id": "status",
                "name": "Did they buy?",
                "action": "checkout_status",
                "inputs": {"checkout_token": "{{trigger.token}}"},
            },
            {
                "id": "remind",
                "name": "Send a reminder (needs approval)",
                "action": "smtp_send_email",
                # Only when we know they did not buy (unknown = no email)
                "when": {"left": "{{steps.status.output.completed}}", "op": "eq", "right": False},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.email}}",
                    "subject": "You left something in your cart",
                    "body": (
                        "Hi {{trigger.customer.first_name}},\n\n"
                        "You still have items waiting in your cart. You can finish your order here:\n"
                        "{{trigger.abandoned_checkout_url}}\n\n"
                        "If you had any trouble at checkout, just reply to this email.\n\nKind regards"
                    ),
                },
            },
        ],
    },
}

REVIEW_REPLY = {
    "slug": "review-reply-assistant",
    "name": "Review reply assistant",
    "category": "E-commerce",
    "requires": [
        "A webhook from your review app (rating, body, reviewer_name, reviewer_email, product_title)",
        "An AI provider configured on the server",
        "An email connection named \"mailbox\"",
    ],
    "description": (
        "When a product review arrives, AI judges its mood and drafts a personal reply. "
        "You check and approve every reply before it is emailed."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_REVIEW},
        "steps": [
            {
                "id": "mood",
                "name": "How does the customer feel?",
                "action": "ai_classify",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "text": "Rating {{trigger.rating}}/5. {{trigger.title}}. {{trigger.body}}",
                    "categories": ["happy", "disappointed", "angry", "unclear"],
                },
            },
            {
                "id": "draft",
                "name": "Draft a reply",
                "action": "ai_draft_reply",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "message": "{{trigger.body}}",
                    "tone": "warm and personal",
                    "instructions": (
                        "Reply to a {{trigger.rating}}-star review of {{trigger.product_title}} by "
                        "{{trigger.reviewer_name}}. The customer seems {{steps.mood.output.category}}. "
                        "Thank them. If they are unhappy, apologise sincerely and invite them to reply "
                        "so we can help. Do not offer refunds or discounts."
                    ),
                },
            },
            {
                "id": "send",
                "name": "Email the reply (needs approval)",
                "action": "smtp_send_email",
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.reviewer_email}}",
                    "subject": "{{steps.draft.output.subject}}",
                    "body": "{{steps.draft.output.body}}",
                },
            },
        ],
    },
}

ECOMMERCE_TEMPLATES = (ORDER_TO_INVOICE, ABANDONED_CART, REVIEW_REPLY)
