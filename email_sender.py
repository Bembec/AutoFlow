"""
Sends approved AutoFlow email previews through Gmail.

For safety, every email is currently redirected to the test recipient.
No customer receives a real email during development.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv


# Load private Gmail settings from .env
load_dotenv()

email_address = os.getenv("EMAIL_ADDRESS")
email_password = os.getenv("EMAIL_APP_PASSWORD")
test_recipient = os.getenv("EMAIL_TEST_RECIPIENT")


def send_email(email_preview):
    """Send one approved email preview to the test recipient."""

    # Read the safety switch whenever this function runs
    sending_enabled = os.getenv(
        "EMAIL_SEND_ENABLED", "false"
    ).lower()

    if sending_enabled != "true":
        print("Email not sent: EMAIL_SEND_ENABLED is false.")
        return False

    if not all([email_address, email_password, test_recipient]):
        print("Email not sent: Gmail configuration is missing.")
        return False

    original_recipient = email_preview["to"]

    message = EmailMessage()
    message["From"] = email_address

    # Redirect to your Gmail during testing
    message["To"] = test_recipient
    message["Subject"] = (
        f"[TEST for {original_recipient}] "
        f"{email_preview['subject']}"
    )
    message.set_content(email_preview["body"])

    secure_context = ssl.create_default_context()

    try:
        # Connect securely, log in and send the email
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=secure_context
        ) as server:
            server.login(email_address, email_password)
            server.send_message(message)

        print("Test email sent for:", original_recipient)
        return True

    except (smtplib.SMTPException, OSError) as error:
        print("Could not send email:", error)
        return False