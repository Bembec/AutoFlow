"""
Ready-made workflows that can be installed into a workspace in one click.
"""

ENQUIRY_TRIAGE = {
    "slug": "customer-enquiry-triage",
    "name": "Customer enquiry triage",
    "category": "General",
    "requires": [],
    "description": (
        "Classify a customer enquiry, add a USD quote for sales enquiries, "
        "save the customer and send a reply after human approval."
    ),
    "definition": {
        "trigger": {
            "type": "manual",
            "sample_payload": {
                "name": "Ada",
                "email": "ada@example.com",
                "message": "I want to know your price",
            },
        },
        "steps": [
            {
                "id": "classify",
                "name": "Classify the enquiry",
                "action": "classify_enquiry",
                "inputs": {"message": "{{trigger.message}}"},
                "retry": {"max_attempts": 2, "backoff_seconds": 1},
            },
            {
                "id": "quote",
                "name": "Quote in USD (sales only)",
                "action": "exchange_rate_quote",
                "inputs": {"amount_eur": 100},
                "when": {"left": "{{steps.classify.output.category}}", "op": "eq", "right": "Sales"},
                "retry": {"max_attempts": 3, "backoff_seconds": 2},
            },
            {
                "id": "save",
                "name": "Save the customer",
                "action": "save_customer",
                "inputs": {
                    "name": "{{trigger.name}}",
                    "email": "{{trigger.email}}",
                    "message": "{{trigger.message}}",
                    "category": "{{steps.classify.output.category}}",
                    "classification_source": "{{steps.classify.output.source}}",
                    "classification_reason": "{{steps.classify.output.reason}}",
                    "quote_eur": "{{steps.quote.output.amount_eur}}",
                    "quote_usd": "{{steps.quote.output.amount_usd}}",
                    "rate_date": "{{steps.quote.output.rate_date}}",
                },
            },
            {
                "id": "compose",
                "name": "Write the reply",
                "action": "compose_email",
                "inputs": {
                    "name": "{{trigger.name}}",
                    "email": "{{trigger.email}}",
                    "category": "{{steps.classify.output.category}}",
                    "quote_usd": "{{steps.quote.output.amount_usd}}",
                },
            },
            {
                "id": "send",
                "name": "Send the reply (needs approval)",
                "action": "send_email",
                "inputs": {
                    "to": "{{steps.compose.output.to}}",
                    "subject": "{{steps.compose.output.subject}}",
                    "body": "{{steps.compose.output.body}}",
                },
            },
        ],
    },
}

from luphina.engine.templates_assistants import ASSISTANT_TEMPLATES  # noqa: E402
from luphina.engine.templates_ecommerce import ECOMMERCE_TEMPLATES  # noqa: E402
from luphina.engine.templates_ecommerce_extra import EXTRA_ECOMMERCE_TEMPLATES  # noqa: E402
from luphina.engine.templates_ecommerce_four import FOURTH_ECOMMERCE_TEMPLATES  # noqa: E402
from luphina.engine.templates_ecommerce_more import MORE_ECOMMERCE_TEMPLATES  # noqa: E402

TEMPLATES = {
    template["slug"]: template
    for template in (
        *ECOMMERCE_TEMPLATES, *MORE_ECOMMERCE_TEMPLATES, *EXTRA_ECOMMERCE_TEMPLATES, *FOURTH_ECOMMERCE_TEMPLATES,
        *ASSISTANT_TEMPLATES,
        ENQUIRY_TRIAGE,
    )
}
