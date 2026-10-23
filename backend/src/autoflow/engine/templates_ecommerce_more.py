"""
More e-commerce templates (V37): the everyday jobs after invoicing.

Templates that use comparisons or loops carry "feature": "smarter_logic";
they are offered only where that feature is switched on. All sample data
is fake, so every template can be test-run straight after installing.
"""

from autoflow.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER

SMART = "smarter_logic"

# Shopify "fulfillment created" webhook (fake data, fields we use)
SAMPLE_FULFILLMENT = {
    "order_id": 820982911946154508,
    "name": "#1001.1",
    "email": "ada@example.com",
    "tracking_company": "Royal Mail",
    "tracking_number": "RM123456789GB",
    "tracking_url": "https://tracking.example/RM123456789GB",
    "destination": {"first_name": "Ada", "city": "London"},
}

SHIPPING_NOTICE = {
    "slug": "shipping-notification",
    "name": "Shipping notification",
    "category": "E-commerce",
    "requires": [
        "A webhook from your store's \"fulfillment created\" event (order_id, email, tracking_number, tracking_url)",
        "An email connection named \"mailbox\"",
    ],
    "description": (
        "When an order ships, email the customer the carrier and tracking link (after your approval). "
        "Orders shipped without tracking get no email."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_FULFILLMENT},
        "steps": [
            {
                "id": "send",
                "name": "Email the tracking link (needs approval)",
                "action": "smtp_send_email",
                "when": {"left": "{{trigger.tracking_number}}", "op": "exists"},
                "retry": {"max_attempts": 2, "backoff_seconds": 5},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.email}}",
                    "subject": "Your order {{trigger.name}} is on its way",
                    "body": (
                        "Hi {{trigger.destination.first_name}},\n\n"
                        "Good news: your order {{trigger.name}} has shipped with {{trigger.tracking_company}}.\n"
                        "Track it here: {{trigger.tracking_url}}\n\nKind regards"
                    ),
                },
            },
        ],
    },
}

# Refund webhook (fake data): Shopify "refunds/create" sends order_id
SAMPLE_REFUND = {"order_id": 820982911946154508, "note": "Item arrived damaged", "amount": "47.60"}

REFUND_VOID = {
    "slug": "refund-void-invoice",
    "name": "Refund → void invoice",
    "category": "E-commerce",
    "requires": [
        "A webhook from your store's \"refund created\" event (with the order_id)",
        "The \"Order → invoice\" workflow (it created the invoice being voided)",
        "An email connection named \"mailbox\"",
    ],
    "description": (
        "When an order is refunded, void its invoice so your books stay right (the number is kept), "
        "then email the customer that the refund is on its way (after your approval)."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_REFUND},
        "steps": [
            {
                "id": "void",
                "name": "Void the invoice",
                "action": "void_invoice",
                "inputs": {"order_ref": "{{trigger.order_id}}", "reason": "Refunded: {{trigger.note}}"},
            },
            {
                "id": "send",
                "name": "Tell the customer (needs approval)",
                "action": "smtp_send_email",
                # Only the first time: a repeated refund webhook sends nothing
                "when": {"left": "{{steps.void.output.voided}}", "op": "eq", "right": True},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{steps.void.output.customer_email}}",
                    "subject": "Your refund is on its way",
                    "body": (
                        "Hello,\n\nWe have refunded your order. Invoice {{steps.void.output.invoice_number}} "
                        "is now void, so there is nothing to pay. The money should reach you within a few days.\n\n"
                        "Kind regards"
                    ),
                },
            },
        ],
    },
}

WEEKLY_SALES = {
    "slug": "weekly-sales-summary",
    "name": "Weekly sales summary",
    "category": "E-commerce",
    "requires": [
        "An API connection named \"shop-api\" whose base_url serves last week's orders at /orders/last-week",
        "An AI provider configured on the server",
        "An email connection named \"mailbox\"; change the To address in the last step to your own",
    ],
    "description": (
        "Every Monday at 9:00 (UTC), fetch last week's orders and email you a short, plain summary: "
        "revenue, best sellers and anything unusual."
    ),
    "definition": {
        "trigger": {
            "type": "schedule",
            "schedule": "0 9 * * 1",
            "sample_payload": {"week": "2026-W42"},
        },
        "steps": [
            {
                "id": "orders",
                "name": "Get last week's orders",
                "action": "http_get",
                "retry": {"max_attempts": 3, "backoff_seconds": 10},
                "inputs": {"connection": "shop-api", "url": "/orders/last-week"},
            },
            {
                "id": "summary",
                "name": "Summarise the week",
                "action": "ai_summarize",
                "inputs": {
                    "text": (
                        "Orders from the shop last week, as JSON:\n{{steps.orders.output.body}}\n\n"
                        "Write a short summary for the shop owner: total revenue, number of orders, "
                        "best-selling products and anything unusual."
                    ),
                    "max_words": 150,
                },
            },
            {
                "id": "send",
                "name": "Email me the summary (needs approval)",
                "action": "smtp_send_email",
                "inputs": {
                    "connection": "mailbox",
                    "to": "owner@your-shop.example",
                    "subject": "Your week in sales",
                    "body": "{{steps.summary.output.summary}}",
                },
            },
        ],
    },
}

LOW_STOCK = {
    "slug": "low-stock-alert",
    "name": "Low-stock alert",
    "category": "E-commerce",
    "feature": SMART,
    "requires": [
        "An API connection named \"shop-api\" whose base_url serves stock levels at /stock",
        "An AI provider configured on the server",
        "An email connection named \"mailbox\"; change the To address in the last step to your own",
    ],
    "description": (
        "Every morning at 7:00 (UTC), check stock levels and email you the products with fewer than 5 left. "
        "No email on days when everything is stocked."
    ),
    "definition": {
        "trigger": {"type": "schedule", "schedule": "0 7 * * *", "sample_payload": {}},
        "steps": [
            {
                "id": "stock",
                "name": "Get stock levels",
                "action": "http_get",
                "retry": {"max_attempts": 3, "backoff_seconds": 10},
                "inputs": {"connection": "shop-api", "url": "/stock"},
            },
            {
                "id": "low",
                "name": "Find what's running low",
                "action": "ai_summarize",
                "inputs": {
                    "text": (
                        "Stock levels as JSON:\n{{steps.stock.output.body}}\n\n"
                        "List every product with fewer than 5 units left, one per line with its count. "
                        "If there are none, reply exactly: ALL STOCKED"
                    ),
                    "max_words": 120,
                },
            },
            {
                "id": "send",
                "name": "Email me the list (needs approval)",
                "action": "smtp_send_email",
                "when": {"left": "{{steps.low.output.summary}}", "op": "not_contains", "right": "ALL STOCKED"},
                "inputs": {
                    "connection": "mailbox",
                    "to": "owner@your-shop.example",
                    "subject": "Running low on stock",
                    "body": "These products are running low:\n\n{{steps.low.output.summary}}",
                },
            },
        ],
    },
}

LINE_ITEMS_SHEET = {
    "slug": "order-lines-to-sheet",
    "name": "Order lines → stock sheet",
    "category": "E-commerce",
    "feature": SMART,
    "requires": [
        "A webhook from your store's \"order paid\" event",
        "A Google connection named \"sheets\" and your spreadsheet id in the step",
    ],
    "description": (
        "For every paid order, add one row per product to your stock sheet: order, product, quantity and "
        "price. Each line is written once, even if the store resends the order."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_SHOPIFY_ORDER},
        "steps": [
            {
                "id": "rows",
                "name": "One row per product",
                "action": "google_sheets_append_row",
                "for_each": "{{trigger.line_items}}",
                "retry": {"max_attempts": 3, "backoff_seconds": 5},
                "inputs": {
                    "connection": "sheets",
                    "spreadsheet_id": "PASTE-YOUR-SPREADSHEET-ID",
                    "sheet_name": "Sold items",
                    "values": ["{{trigger.name}}", "{{item.title}}", "{{item.quantity}}", "{{item.price}}"],
                },
            },
        ],
    },
}

VIP_THANKS = {
    "slug": "vip-thank-you",
    "name": "Big-order thank-you",
    "category": "E-commerce",
    "feature": SMART,
    "requires": [
        "A webhook from your store's \"order paid\" event",
        "An email connection named \"mailbox\"",
    ],
    "description": (
        "When an order over 150 is paid, send the customer a personal thank-you from you (after your "
        "approval). Change the amount in the step's condition."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": {**SAMPLE_SHOPIFY_ORDER, "total_price": "180.00"}},
        "steps": [
            {
                "id": "send",
                "name": "Personal thank-you (needs approval)",
                "action": "smtp_send_email",
                "when": {"all": [
                    {"left": "{{trigger.total_price}}", "op": "gt", "right": 150},
                    {"left": "{{trigger.email}}", "op": "exists"},
                ]},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.email}}",
                    "subject": "Thank you, {{trigger.customer.first_name}}",
                    "body": (
                        "Hi {{trigger.customer.first_name}},\n\n"
                        "I saw your order {{trigger.name}} come in and wanted to say a personal thank you. "
                        "Small shops like ours run on customers like you. If anything isn't perfect, just "
                        "reply to this email.\n\nWarm regards"
                    ),
                },
            },
        ],
    },
}

SAMPLE_SUPPORT_EMAIL = {
    "from": "Grace Hopper <grace@example.com>",
    "from_address": "grace@example.com",
    "to": "support@your-shop.example",
    "subject": "Wrong size",
    "date": "Thu, 22 Oct 2026 10:15:00 +0000",
    "message_id": "<demo-support-1@example.com>",
    "text": "Hi, the linen tote I ordered (#1002) is too small. Can I send it back and get the bigger one?",
    "attachments": [],
    "attachments_text": "",
}

SUPPORT_TRIAGE = {
    "slug": "support-inbox-assistant",
    "name": "Support inbox assistant",
    "category": "E-commerce",
    "requires": [
        "An incoming email connection named \"support-inbox\"",
        "An AI provider configured on the server",
        "An email connection named \"mailbox\"",
    ],
    "description": (
        "When a customer emails your support inbox, AI sorts it (return, delivery, complaint, product "
        "question) and drafts a reply in your tone. You approve every reply before it goes out."
    ),
    "definition": {
        "trigger": {"type": "email", "connection": "support-inbox", "sample_payload": SAMPLE_SUPPORT_EMAIL},
        "steps": [
            {
                "id": "kind",
                "name": "What is it about?",
                "action": "ai_classify",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "text": "{{trigger.subject}}\n\n{{trigger.text}}",
                    "categories": ["return or exchange", "delivery question", "complaint", "product question", "other"],
                },
            },
            {
                "id": "draft",
                "name": "Draft a reply",
                "action": "ai_draft_reply",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "message": "{{trigger.text}}",
                    "tone": "friendly and helpful",
                    "instructions": (
                        "This is a {{steps.kind.output.category}} from a customer of our online shop. "
                        "Answer helpfully and briefly. Never promise refunds, discounts or dates; say we "
                        "will check and come back if unsure."
                    ),
                },
            },
            {
                "id": "send",
                "name": "Send the reply (needs approval)",
                "action": "smtp_send_email",
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{trigger.from_address}}",
                    "subject": "Re: {{trigger.subject}}",
                    "body": "{{steps.draft.output.body}}",
                },
            },
        ],
    },
}

SAMPLE_WOO_PROCESSING = {
    "id": 728,
    "number": "728",
    "status": "processing",
    "billing": {"first_name": "Alan", "email": "alan@example.com"},
}

WOO_PACKING_NOTE = {
    "slug": "woocommerce-packing-note",
    "name": "WooCommerce \"we're packing it\" note",
    "category": "E-commerce",
    "requires": [
        "A WooCommerce webhook (topic \"Order updated\") with the signature type WooCommerce",
        "A WooCommerce connection named \"store\"",
    ],
    "description": (
        "When a WooCommerce order starts processing, add a note the customer can see: thanks, we're "
        "packing your order. WooCommerce emails it to them."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_WOO_PROCESSING},
        "steps": [
            {
                "id": "note",
                "name": "Add a customer note",
                "action": "woocommerce_add_order_note",
                "when": {"left": "{{trigger.status}}", "op": "eq", "right": "processing"},
                "inputs": {
                    "connection": "store",
                    "order_id": "{{trigger.id}}",
                    "note": "Thanks for your order, {{trigger.billing.first_name}}! We're packing it now.",
                    "customer_note": True,
                },
            },
        ],
    },
}

MORE_ECOMMERCE_TEMPLATES = (
    SHIPPING_NOTICE,
    REFUND_VOID,
    WEEKLY_SALES,
    LOW_STOCK,
    LINE_ITEMS_SHEET,
    VIP_THANKS,
    SUPPORT_TRIAGE,
    WOO_PACKING_NOTE,
)
