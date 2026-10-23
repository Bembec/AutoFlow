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
                # Only for a new invoice: a repeated order webhook sends no second email
                "when": {"left": "{{steps.invoice.output.created}}", "op": "eq", "right": True},
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

SAMPLE_SUPPLIER_EMAIL = {
    "from": "Beans Wholesale <billing@beans.example>",
    "subject": "Invoice SUP-4471",
    "text": "Hello, please find our invoice attached. Kind regards, Beans Wholesale",
    "attachments": [{"filename": "SUP-4471.pdf", "content_type": "application/pdf"}],
    "attachments_text": (
        "--- SUP-4471.pdf ---\nBeans Wholesale Ltd\nInvoice SUP-4471\nDate: 14 Oct 2026\n"
        "Due: 13 Nov 2026\nColombian beans 10 kg  120.00\nVAT 20%  24.00\nTotal due EUR 144.00"
    ),
}

SUPPLIER_INVOICE_TO_SHEET = {
    "slug": "supplier-invoice-to-sheet",
    "name": "Supplier invoice → spreadsheet",
    "category": "E-commerce",
    "requires": [
        "An incoming email connection named \"invoices-inbox\" (or switch the trigger to document upload)",
        "A Google connection named \"sheets\" and your spreadsheet id in the last step",
        "An AI provider configured on the server",
    ],
    "description": (
        "When a supplier emails an invoice (PDF, scan or text), AI reads the invoice number, "
        "dates and amounts and adds a row to your bookkeeping sheet. Unsure results wait for your check."
    ),
    "definition": {
        "trigger": {"type": "email", "connection": "invoices-inbox", "sample_payload": SAMPLE_SUPPLIER_EMAIL},
        "steps": [
            {
                "id": "extract",
                "name": "Read the invoice",
                "action": "ai_extract",
                "retry": {"max_attempts": 2, "backoff_seconds": 2},
                "inputs": {
                    "text": "{{trigger.text}}\n\n{{trigger.attachments_text}}",
                    "fields": [
                        {"name": "supplier", "description": "company that sent the invoice"},
                        {"name": "invoice_number"},
                        {"name": "invoice_date", "description": "as YYYY-MM-DD"},
                        {"name": "due_date", "description": "as YYYY-MM-DD"},
                        {"name": "total", "description": "amount due, number only"},
                        {"name": "currency", "description": "3-letter code"},
                    ],
                },
            },
            {
                "id": "row",
                "name": "Add to the bookkeeping sheet",
                "action": "google_sheets_append_row",
                "inputs": {
                    "connection": "sheets",
                    "spreadsheet_id": "PASTE-YOUR-SPREADSHEET-ID",
                    "sheet_name": "Supplier invoices",
                    "values": [
                        "{{steps.extract.output.data.invoice_date}}",
                        "{{steps.extract.output.data.supplier}}",
                        "{{steps.extract.output.data.invoice_number}}",
                        "{{steps.extract.output.data.total}}",
                        "{{steps.extract.output.data.currency}}",
                        "{{steps.extract.output.data.due_date}}",
                    ],
                },
            },
        ],
    },
}

# Example of a WooCommerce order webhook (fake data)
SAMPLE_WOOCOMMERCE_ORDER = {
    "id": 727,
    "number": "727",
    "status": "processing",
    "currency": "EUR",
    "total": "47.60",
    "total_tax": "7.60",
    "cart_hash": "b1f4c9e2",
    "billing": {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"},
    "line_items": [
        {"name": "Ceramic mug", "quantity": 2, "subtotal": "24.00", "total": "24.00", "price": 12},
        {"name": "Coffee beans 250 g", "quantity": 1, "subtotal": "16.00", "total": "16.00", "price": 16},
    ],
}

WOOCOMMERCE_ORDER_TO_INVOICE = {
    "slug": "woocommerce-order-to-invoice",
    "name": "WooCommerce order → invoice",
    "category": "E-commerce",
    "requires": [
        "A WooCommerce webhook (topic \"Order updated\" or \"Order created\") with the signature type WooCommerce",
        "An email connection named \"mailbox\"",
        "Your business details in Settings (printed on invoices)",
    ],
    "description": (
        "When a WooCommerce order is processing, create a numbered invoice and email the customer "
        "a link to it (after your approval). Each order gets one invoice, however often it updates."
    ),
    "definition": {
        "trigger": {"type": "webhook", "sample_payload": SAMPLE_WOOCOMMERCE_ORDER},
        "steps": [
            {
                "id": "invoice",
                "name": "Create the invoice",
                "action": "create_invoice",
                # Only paid orders: WooCommerce marks them "processing" (or "completed")
                "when": {"left": "{{trigger.status}}", "op": "neq", "right": "pending"},
                "inputs": {"order": "{{trigger}}"},
            },
            {
                "id": "track",
                "name": "Record the order",
                "action": "record_order",
                "inputs": {"checkout_token": "{{trigger.cart_hash}}", "email": "{{trigger.billing.email}}"},
            },
            {
                "id": "send",
                "name": "Email the invoice (needs approval)",
                "action": "smtp_send_email",
                "when": {"left": "{{steps.invoice.output.created}}", "op": "eq", "right": True},
                "inputs": {
                    "connection": "mailbox",
                    "to": "{{steps.invoice.output.customer_email}}",
                    "subject": "Your invoice {{steps.invoice.output.invoice_number}} for order {{trigger.number}}",
                    "body": (
                        "Hi {{trigger.billing.first_name}},\n\n"
                        "Thank you for your order {{trigger.number}}. Your invoice "
                        "{{steps.invoice.output.invoice_number}} for {{steps.invoice.output.total}} "
                        "{{steps.invoice.output.currency}} is here:\n{{steps.invoice.output.url}}\n\n"
                        "Kind regards"
                    ),
                },
            },
        ],
    },
}

ECOMMERCE_TEMPLATES = (
    ORDER_TO_INVOICE,
    WOOCOMMERCE_ORDER_TO_INVOICE,
    ABANDONED_CART,
    REVIEW_REPLY,
    SUPPLIER_INVOICE_TO_SHEET,
)
