"""
E-commerce templates, part three (V41): customers, records and follow-ups.

Same rules as the other packs: fake sample data so every template can be
test-run at once, emails always wait for approval, and templates that use
comparisons carry "feature": "smarter_logic".
"""

from luphina.engine.templates_ecommerce import SAMPLE_REVIEW, SAMPLE_SHOPIFY_ORDER, SAMPLE_WOOCOMMERCE_ORDER

SMART = "smarter_logic"
MAILBOX = "An email connection named \"mailbox\""
ORDER_PAID_WEBHOOK = "A webhook from your store's \"order paid\" event"

# A first-time buyer (Shopify includes the customer's order count)
SAMPLE_FIRST_ORDER = {
    **SAMPLE_SHOPIFY_ORDER,
    "customer": {**SAMPLE_SHOPIFY_ORDER["customer"], "orders_count": 1},
}


def _email(to, subject, body, step_id="send", name="Send the email (needs approval)", when=None):
    step = {
        "id": step_id,
        "name": name,
        "action": "smtp_send_email",
        "retry": {"max_attempts": 2, "backoff_seconds": 5},
        "inputs": {"connection": "mailbox", "to": to, "subject": subject, "body": body},
    }
    if when:
        step["when"] = when
    return step


FIRST_ORDER_WELCOME = {
    "slug": "first-order-welcome",
    "name": "Welcome first-time customers",
    "category": "E-commerce",
    "requires": [ORDER_PAID_WEBHOOK + " (Shopify sends the customer's orders_count)", MAILBOX],
    "description": (
        "When someone buys from you for the first time, send a warm welcome that tells them what happens "
        "next (after your approval). Returning customers get nothing extra."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_FIRST_ORDER},
        "steps": [_email(
            "{{trigger.email}}",
            "Welcome, {{trigger.customer.first_name}}!",
            "Hi {{trigger.customer.first_name}},\n\nThank you for your first order with us ({{trigger.name}}). "
            "We're packing it now and you'll get a tracking link as soon as it ships.\n\n"
            "If you have any questions, just reply to this email.\n\nKind regards",
            when={"left": "{{trigger.customer.orders_count}}", "op": "eq", "right": 1},
        )],
    },
}

REVIEW_REQUEST = {
    "slug": "review-request-later",
    "name": "Ask for a review a week later",
    "category": "E-commerce",
    "requires": [ORDER_PAID_WEBHOOK, MAILBOX, "The background worker (for the 7-day wait)"],
    "description": (
        "Seven days after an order is paid, ask the customer how they like it and invite a review "
        "(after your approval). Change the wait in the first step."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_ORDER},
        "steps": [
            {"id": "wait", "name": "Wait a week", "action": "delay", "inputs": {"days": 7}},
            _email(
                "{{trigger.email}}",
                "How are you getting on with your order?",
                "Hi {{trigger.customer.first_name}},\n\nYour order {{trigger.name}} should have arrived by now. "
                "We'd love to hear what you think: a short review helps other customers and helps us improve.\n\n"
                "Thank you!",
            ),
        ],
    },
}

ORDERS_TO_SHEET = {
    "slug": "orders-to-sheet",
    "name": "Orders → spreadsheet",
    "category": "E-commerce",
    "requires": [ORDER_PAID_WEBHOOK, "A Google connection named \"sheets\" and your spreadsheet id in the step"],
    "description": "Add one row per paid order to a Google Sheet: date, order number, customer, email and total.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_SHOPIFY_ORDER, "created_at": "2026-10-22T10:15:00Z"}},
        "steps": [{
            "id": "row",
            "name": "Add the order to the sheet",
            "action": "google_sheets_append_row",
            "retry": {"max_attempts": 3, "backoff_seconds": 5},
            "inputs": {
                "connection": "sheets",
                "spreadsheet_id": "PASTE-YOUR-SPREADSHEET-ID",
                "sheet_name": "Orders",
                "values": ["{{trigger.created_at}}", "{{trigger.name}}",
                           "{{trigger.customer.first_name}} {{trigger.customer.last_name}}",
                           "{{trigger.email}}", "{{trigger.total_price}}", "{{trigger.currency}}"],
            },
        }],
    },
}

WOO_ORDERS_TO_SHEET = {
    "slug": "woocommerce-orders-to-sheet",
    "name": "WooCommerce orders → spreadsheet",
    "category": "E-commerce",
    "requires": [
        "A WooCommerce webhook (topic \"Order created\") with the signature type WooCommerce",
        "A Google connection named \"sheets\" and your spreadsheet id in the step",
    ],
    "description": "Add one row per WooCommerce order to a Google Sheet: order number, status, customer and total.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_WOOCOMMERCE_ORDER},
        "steps": [{
            "id": "row",
            "name": "Add the order to the sheet",
            "action": "google_sheets_append_row",
            "retry": {"max_attempts": 3, "backoff_seconds": 5},
            "inputs": {
                "connection": "sheets",
                "spreadsheet_id": "PASTE-YOUR-SPREADSHEET-ID",
                "sheet_name": "Orders",
                "values": ["{{trigger.number}}", "{{trigger.status}}",
                           "{{trigger.billing.first_name}} {{trigger.billing.last_name}}",
                           "{{trigger.billing.email}}", "{{trigger.total}}", "{{trigger.currency}}"],
            },
        }],
    },
}

CUSTOMERS_TO_AIRTABLE = {
    "slug": "customers-to-airtable",
    "name": "Customers → Airtable",
    "category": "E-commerce",
    "requires": [ORDER_PAID_WEBHOOK, "An Airtable connection named \"crm\" with a \"Customers\" table"],
    "description": (
        "Keep a customer list in Airtable: each paid order adds the customer, or updates them if they're "
        "already there (matched by email)."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_ORDER},
        "steps": [{
            "id": "customer",
            "name": "Add or update the customer",
            "action": "airtable_upsert",
            "retry": {"max_attempts": 3, "backoff_seconds": 5},
            "inputs": {
                "connection": "crm",
                "table": "Customers",
                "match_field": "Email",
                "fields": {
                    "Email": "{{trigger.email}}",
                    "Name": "{{trigger.customer.first_name}} {{trigger.customer.last_name}}",
                    "Last order": "{{trigger.name}}",
                    "Last order total": "{{trigger.total_price}}",
                },
            },
        }],
    },
}

TAG_BIG_ORDERS = {
    "slug": "tag-big-orders",
    "name": "Tag big orders",
    "category": "E-commerce",
    "feature": SMART,
    "requires": [ORDER_PAID_WEBHOOK, "A Shopify connection named \"store\""],
    "description": (
        "Tag Shopify orders over 150 as \"big-order\" so your team packs them first. "
        "Change the amount in the step's condition."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_SHOPIFY_ORDER, "total_price": "180.00"}},
        "steps": [{
            "id": "tag",
            "name": "Tag the order",
            "action": "shopify_tag_order",
            "when": {"left": "{{trigger.total_price}}", "op": "gt", "right": 150},
            "inputs": {"connection": "store", "order_id": "{{trigger.id}}", "tags": "big-order"},
        }],
    },
}

LOW_RATING_ALERT = {
    "slug": "low-rating-alert",
    "name": "Bad review alert",
    "category": "E-commerce",
    "feature": SMART,
    "requires": ["A webhook from your review app (rating, body, reviewer_name, product_title)", MAILBOX,
                 "Your own address in the step's To field"],
    "description": "When a review of 2 stars or less comes in, email you straight away so you can put it right.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_REVIEW, "rating": 2}},
        "steps": [_email(
            "owner@your-shop.example",
            "{{trigger.rating}}-star review of {{trigger.product_title}}",
            "{{trigger.reviewer_name}} left a {{trigger.rating}}-star review of {{trigger.product_title}}:\n\n"
            "\"{{trigger.body}}\"\n\nReply soon: a quick, kind answer often turns an unhappy customer around.",
            name="Email me (needs approval)",
            when={"left": "{{trigger.rating}}", "op": "lte", "right": 2},
        )],
    },
}

SAMPLE_PAYMENT_FAILED = {
    "order_id": 820982911946154508,
    "name": "#1001",
    "email": "ada@example.com",
    "first_name": "Ada",
    "amount": "47.60",
    "currency": "EUR",
    "pay_url": "https://shop.example/orders/1001/pay",
}

PAYMENT_FAILED = {
    "slug": "payment-failed-reminder",
    "name": "Payment failed reminder",
    "category": "E-commerce",
    "requires": ["A webhook from your store or payment provider when a payment fails (email, pay_url)", MAILBOX],
    "description": (
        "When a payment fails, send the customer a friendly note with a link to pay again on your own shop "
        "(after your approval)."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_PAYMENT_FAILED},
        "steps": [_email(
            "{{trigger.email}}",
            "There was a problem with your payment for order {{trigger.name}}",
            "Hi {{trigger.first_name}},\n\nThe payment of {{trigger.amount}} {{trigger.currency}} for your order "
            "{{trigger.name}} didn't go through. No money was taken. You can try again here:\n"
            "{{trigger.pay_url}}\n\nKind regards",
            when={"left": "{{trigger.pay_url}}", "op": "exists"},
        )],
    },
}

WOO_COMPLETED_THANKS = {
    "slug": "woocommerce-completed-thanks",
    "name": "WooCommerce completed: thank you",
    "category": "E-commerce",
    "requires": ["A WooCommerce webhook (topic \"Order updated\") with the signature type WooCommerce", MAILBOX],
    "description": "When a WooCommerce order is marked completed, thank the customer and invite a review (after your approval).",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_WOOCOMMERCE_ORDER, "status": "completed"}},
        "steps": [_email(
            "{{trigger.billing.email}}",
            "Thank you for your order {{trigger.number}}",
            "Hi {{trigger.billing.first_name}},\n\nYour order {{trigger.number}} is complete. Thank you for "
            "shopping with us! If you have a minute, a short review would mean a lot.\n\nKind regards",
            when={"left": "{{trigger.status}}", "op": "eq", "right": "completed"},
        )],
    },
}

WOO_CANCELLED = {
    "slug": "woocommerce-cancelled-void",
    "name": "WooCommerce cancelled → void invoice",
    "category": "E-commerce",
    "requires": [
        "A WooCommerce webhook (topic \"Order updated\") with the signature type WooCommerce",
        "The \"WooCommerce order → invoice\" workflow (it created the invoice)",
    ],
    "description": "When a WooCommerce order is cancelled or refunded, void its invoice. The number is kept for your books.",
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_WOOCOMMERCE_ORDER, "status": "cancelled"}},
        "steps": [{
            "id": "void",
            "name": "Void the invoice",
            "action": "void_invoice",
            "when": {"any": [
                {"left": "{{trigger.status}}", "op": "eq", "right": "cancelled"},
                {"left": "{{trigger.status}}", "op": "eq", "right": "refunded"},
            ]},
            "inputs": {"order_ref": "{{trigger.id}}", "reason": "Order {{trigger.status}} in WooCommerce"},
        }],
    },
    "feature": SMART,
}

SAMPLE_WHOLESALE_EMAIL = {
    "from": "Linus Pauling <buyer@cafe-chain.example>",
    "from_address": "buyer@cafe-chain.example",
    "to": "hello@your-shop.example",
    "subject": "Bulk order of mugs?",
    "date": "Thu, 22 Oct 2026 09:00:00 +0000",
    "message_id": "<demo-wholesale-1@example.com>",
    "text": "Hello, we run 12 cafes and would like 400 of your ceramic mugs with our logo. What would that cost?",
    "attachments": [],
    "attachments_text": "",
}

WHOLESALE_LEADS = {
    "slug": "wholesale-lead-alert",
    "name": "Wholesale lead alert",
    "category": "E-commerce",
    "requires": [
        "An incoming email connection named \"shop-inbox\"",
        "An AI provider configured on the server",
        MAILBOX,
        "Your own address in the last step's To field",
    ],
    "description": (
        "AI reads incoming emails and spots wholesale or bulk enquiries. You get a short summary straight "
        "away, so big buyers never wait."
    ),
    "definition": {
        "trigger": {"type": "email", "connection": "shop-inbox", "sample_payload": SAMPLE_WHOLESALE_EMAIL},
        "steps": [
            {
                "id": "kind",
                "name": "Is it a wholesale enquiry?",
                "action": "ai_classify",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "text": "{{trigger.subject}}\n\n{{trigger.text}}",
                    "categories": ["wholesale or bulk enquiry", "normal customer", "other"],
                },
            },
            {
                "id": "summary",
                "name": "Summarise the enquiry",
                "action": "ai_summarize",
                "when": {"left": "{{steps.kind.output.category}}", "op": "eq", "right": "wholesale or bulk enquiry"},
                "inputs": {"text": "From {{trigger.from}}: {{trigger.text}}", "max_words": 60},
            },
            _email(
                "owner@your-shop.example",
                "Wholesale lead: {{trigger.subject}}",
                "{{steps.summary.output.summary}}\n\nFrom: {{trigger.from}}",
                name="Email me (needs approval)",
                when={"left": "{{steps.kind.output.category}}", "op": "eq", "right": "wholesale or bulk enquiry"},
            ),
        ],
    },
}

EXTRA_ECOMMERCE_TEMPLATES = (
    FIRST_ORDER_WELCOME,
    REVIEW_REQUEST,
    ORDERS_TO_SHEET,
    WOO_ORDERS_TO_SHEET,
    CUSTOMERS_TO_AIRTABLE,
    TAG_BIG_ORDERS,
    LOW_RATING_ALERT,
    PAYMENT_FAILED,
    WOO_COMPLETED_THANKS,
    WOO_CANCELLED,
    WHOLESALE_LEADS,
)
