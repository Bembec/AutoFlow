"""
Creates personalized email previews for AutoFlow customers.

This module currently generates text only. It does not send emails.
"""


def create_email_preview(customer):
    """Return a personalized email based on the enquiry category."""

    name = customer["name"].strip()
    email = customer["email"].strip()
    category = customer["category"]

    # Create a Sales response with available quote information
    if category == "Sales":
        quote_usd = customer.get("quote_usd", "")

        subject = "Information about our pricing"

        if quote_usd:
            body = (
                f"Hello {name},\n\n"
                f"Thank you for your interest in our service. "
                f"Our sample €100 price is approximately "
                f"${quote_usd} USD based on the available reference rate.\n\n"
                f"Please let us know if you need more information."
            )
        else:
            body = (
                f"Hello {name},\n\n"
                f"Thank you for your interest in our pricing. "
                f"Our team will provide more information shortly."
            )

    # Create a Support acknowledgement
    elif category == "Support":
        subject = "We received your support request"
        body = (
            f"Hello {name},\n\n"
            f"We have received your support request. "
            f"A member of our team will review it and respond shortly."
        )

    # Create a general response for all other enquiries
    else:
        subject = "Thank you for contacting us"
        body = (
            f"Hello {name},\n\n"
            f"Thank you for contacting us. "
            f"We have received your message and will respond shortly."
        )

    # Return structured email information for later use
    return {
        "to": email,
        "subject": subject,
        "body": body,
    }