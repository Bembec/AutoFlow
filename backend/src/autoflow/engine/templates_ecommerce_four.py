"""
E-commerce templates, part four (V47): cancellations, risk, loyalty and logs.

Same rules as the other packs: fake sample data that makes every step run,
emails wait for approval, comparisons carry "feature": "smarter_logic".
"""

from autoflow.engine.templates_ecommerce import SAMPLE_REVIEW, SAMPLE_SHOPIFY_CHECKOUT, SAMPLE_SHOPIFY_ORDER
from autoflow.engine.templates_ecommerce_extra import MAILBOX, ORDER_PAID_WEBHOOK, SMART, _email
from autoflow.engine.templates_assistants import SAMPLE_SUPPORT_EMAIL

OWNER = "Your own address in the email step's To field"

SHOPIFY_CANCELLED = {
    "slug": "shopify-cancelled-void",
    "name": "Cancelled order → void invoice",
    "category": "E-commerce",
    "requires": ["A webhook from your store's \"order cancelled\" event",
                 "The \"Order → invoice\" workflow (it created the invoice)"],
    "description": "When a Shopify order is cancelled, void its invoice. The number is kept for your books, and it happens once however often the store resends.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_SHOPIFY_ORDER, "cancel_reason": "customer"}},
        "steps": [{
            "id": "void",
            "name": "Void the invoice",
            "action": "void_invoice",
            "inputs": {"order_ref": "{{trigger.id}}", "reason": "Order cancelled ({{trigger.cancel_reason}})"},
        }],
    },
}

DAILY_DIGEST = {
    "slug": "daily-order-digest",
    "name": "Daily order digest",
    "category": "E-commerce",
    "requires": ["An API connection named \"shop-api\" whose base_url serves today's orders at /orders/today",
                 "An AI provider configured on the server", MAILBOX, OWNER],
    "description": "Every evening at 18:00 (UTC), a short summary of the day's orders: how many, revenue, and anything that needs you tomorrow.",
    "definition": {
        "trigger": {"type": "schedule", "schedule": "0 18 * * *", "sample_payload": {"day": "2026-10-22"}},
        "steps": [
            {"id": "orders", "name": "Get today's orders", "action": "http_get",
             "retry": {"max_attempts": 3, "backoff_seconds": 10},
             "inputs": {"connection": "shop-api", "url": "/orders/today"}},
            {"id": "summary", "name": "Summarise the day", "action": "ai_summarize",
             "inputs": {"text": "Today's orders as JSON:\n{{steps.orders.output.body}}\n\nSummarise for the shop owner: "
                                "number of orders, revenue, and anything unusual or needing action tomorrow.",
                        "max_words": 120}},
            _email("owner@your-shop.example", "Today in your shop", "{{steps.summary.output.summary}}",
                   name="Email me the digest (needs approval)"),
        ],
    },
}

SAMPLE_BIG_REFUND = {"order_id": 820982911946154508, "name": "#1001", "amount": "180.00", "currency": "EUR",
                     "note": "Whole order returned"}

BIG_REFUND_ALERT = {
    "slug": "big-refund-alert",
    "name": "Big refund alert",
    "category": "E-commerce",
    "feature": SMART,
    "requires": ["A webhook from your store's \"refund created\" event (with amount)", MAILBOX, OWNER],
    "description": "When a refund over 100 goes through, email you the details so nothing large slips past. Change the amount in the step's condition.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_BIG_REFUND},
        "steps": [_email(
            "owner@your-shop.example",
            "Refund of {{trigger.amount}} {{trigger.currency}} on order {{trigger.name}}",
            "A refund of {{trigger.amount}} {{trigger.currency}} was made on order {{trigger.name}}.\n"
            "Note: {{trigger.note}}",
            name="Email me (needs approval)",
            when={"left": "{{trigger.amount}}", "op": "gt", "right": 100},
        )],
    },
}

SAMPLE_RISKY_ORDER = {
    **SAMPLE_SHOPIFY_ORDER,
    "total_price": "640.00",
    "customer": {**SAMPLE_SHOPIFY_ORDER["customer"], "orders_count": 1},
}
RISKY = {"all": [
    {"left": "{{trigger.total_price}}", "op": "gt", "right": 300},
    {"left": "{{trigger.customer.orders_count}}", "op": "eq", "right": 1},
]}

HIGH_RISK_CHECK = {
    "slug": "high-value-first-order-check",
    "name": "Check big first orders",
    "category": "E-commerce",
    "feature": SMART,
    "requires": [ORDER_PAID_WEBHOOK, "A Shopify connection named \"store\"", MAILBOX, OWNER],
    "description": (
        "A first-time customer placing an order over 300 is tagged \"check-before-shipping\" and you get an "
        "email, so a person looks before it ships. Change the amount in the conditions."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_RISKY_ORDER},
        "steps": [
            {"id": "tag", "name": "Tag the order", "action": "shopify_tag_order", "when": RISKY,
             "inputs": {"connection": "store", "order_id": "{{trigger.id}}", "tags": "check-before-shipping"}},
            _email("owner@your-shop.example", "Check order {{trigger.name}} before shipping",
                   "A first-time customer ({{trigger.email}}) placed an order of {{trigger.total_price}} "
                   "{{trigger.currency}}. It is tagged check-before-shipping in Shopify.",
                   name="Email me (needs approval)", when=RISKY),
        ],
    },
}

SAMPLE_FOREIGN_REVIEW = {**SAMPLE_REVIEW, "rating": 4, "title": "Muy bonita",
                         "body": "La taza es muy bonita, pero llegó un poco tarde."}

FOREIGN_REVIEW_REPLY = {
    "slug": "foreign-review-reply",
    "name": "Reply to reviews in any language",
    "category": "E-commerce",
    "requires": ["A webhook from your review app", "An AI provider configured on the server", MAILBOX],
    "description": (
        "Translates each review into English for you, then drafts a reply in the reviewer's own language. "
        "You read the translation and approve the reply."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_FOREIGN_REVIEW},
        "steps": [
            {"id": "english", "name": "Translate for me", "action": "ai_translate",
             "inputs": {"text": "{{trigger.title}}. {{trigger.body}}", "target_language": "English"}},
            {"id": "draft", "name": "Draft a reply in their language", "action": "ai_draft_reply",
             "inputs": {"message": "{{trigger.body}}", "tone": "warm and personal",
                        "instructions": "Reply in the same language the review is written in. Thank them for "
                                        "the {{trigger.rating}}-star review of {{trigger.product_title}}. Do not "
                                        "offer refunds or discounts."}},
            _email("{{trigger.reviewer_email}}", "{{steps.draft.output.subject}}", "{{steps.draft.output.body}}",
                   name="Send the reply (needs approval)"),
        ],
    },
}

LOYALTY_THANKS = {
    "slug": "loyal-customer-thanks",
    "name": "Thank loyal customers",
    "category": "E-commerce",
    "requires": [ORDER_PAID_WEBHOOK + " (Shopify sends the customer's orders_count)", MAILBOX],
    "description": "On a customer's third order, send a personal thank-you for coming back (after your approval).",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {
            **SAMPLE_SHOPIFY_ORDER, "customer": {**SAMPLE_SHOPIFY_ORDER["customer"], "orders_count": 3}}},
        "steps": [_email(
            "{{trigger.email}}",
            "Thank you for coming back, {{trigger.customer.first_name}}",
            "Hi {{trigger.customer.first_name}},\n\nThis is your third order with us, and we noticed. Thank you for "
            "coming back! Customers like you keep a small shop going.\n\nWarm regards",
            when={"left": "{{trigger.customer.orders_count}}", "op": "eq", "right": 3},
        )],
    },
}

CHECKOUTS_TO_AIRTABLE = {
    "slug": "abandoned-checkouts-to-airtable",
    "name": "Abandoned checkouts → Airtable",
    "category": "E-commerce",
    "requires": ["A webhook from your store's \"checkout created\" event",
                 "An Airtable connection named \"crm\" with a \"Checkouts\" table"],
    "description": "Keep a list of started checkouts in Airtable (email, cart value, recovery link) to see where shoppers drop off.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_CHECKOUT},
        "steps": [{
            "id": "row", "name": "Add the checkout", "action": "airtable_upsert",
            "retry": {"max_attempts": 3, "backoff_seconds": 5},
            "inputs": {"connection": "crm", "table": "Checkouts", "match_field": "Token",
                       "fields": {"Token": "{{trigger.token}}", "Email": "{{trigger.email}}",
                                  "Cart value": "{{trigger.total_price}}",
                                  "Recovery link": "{{trigger.abandoned_checkout_url}}"}},
        }],
    },
}

SUPPORT_LOG = {
    "slug": "support-log-to-sheet",
    "name": "Support emails → log sheet",
    "category": "E-commerce",
    "requires": ["An incoming email connection named \"support-inbox\"", "An AI provider configured on the server",
                 "A Google connection named \"sheets\" and your spreadsheet id in the step"],
    "description": "Every support email becomes a row in a sheet with its topic (return, delivery, complaint, question), so you see what customers ask most.",
    "definition": {
        "trigger": {"type": "email", "connection": "support-inbox", "sample_payload": SAMPLE_SUPPORT_EMAIL},
        "steps": [
            {"id": "topic", "name": "What is it about?", "action": "ai_classify",
             "inputs": {"text": "{{trigger.subject}}\n\n{{trigger.text}}",
                        "categories": ["return or exchange", "delivery question", "complaint", "product question", "other"]}},
            {"id": "row", "name": "Log it", "action": "google_sheets_append_row",
             "retry": {"max_attempts": 3, "backoff_seconds": 5},
             "inputs": {"connection": "sheets", "spreadsheet_id": "PASTE-YOUR-SPREADSHEET-ID", "sheet_name": "Support",
                        "values": ["{{trigger.date}}", "{{trigger.from_address}}", "{{trigger.subject}}",
                                   "{{steps.topic.output.category}}"]}},
        ],
    },
}

FOURTH_ECOMMERCE_TEMPLATES = (
    SHOPIFY_CANCELLED, DAILY_DIGEST, BIG_REFUND_ALERT, HIGH_RISK_CHECK,
    FOREIGN_REVIEW_REPLY, LOYALTY_THANKS, CHECKOUTS_TO_AIRTABLE, SUPPORT_LOG,
)
