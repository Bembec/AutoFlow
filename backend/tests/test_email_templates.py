from autoflow.emails.templates import create_email_preview


def make_customer(category, quote_usd=""):
    return {
        "name": " Ada ",
        "email": " ada@example.com ",
        "category": category,
        "quote_usd": quote_usd,
    }


def test_sales_email_includes_quote():
    preview = create_email_preview(make_customer("Sales", "116.22"))

    assert preview["to"] == "ada@example.com"
    assert preview["subject"] == "Information about our pricing"
    assert "$116.22" in preview["body"]
    assert preview["body"].startswith("Hello Ada,")


def test_sales_email_without_quote():
    preview = create_email_preview(make_customer("Sales"))

    assert "$" not in preview["body"]


def test_support_and_other_subjects():
    assert create_email_preview(make_customer("Support"))["subject"] == (
        "We received your support request"
    )
    assert create_email_preview(make_customer("Other"))["subject"] == (
        "Thank you for contacting us"
    )
