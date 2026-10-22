"""
AutoFlow AI — Customer enquiry workflow

Reads customer enquiries from a CSV file, classifies them (AI with human
review, or keyword rules), adds EUR-to-USD sample quotes to Sales
enquiries, stores the results in SQLite and CSV, sends one approved test
email, synchronizes Airtable and records the activity.

Run with:  python -m autoflow

When run without a terminal (interactive=False, e.g. from the API), AI
suggestions are stored as "AI Pending Review" and no email is sent.
"""

import csv

from autoflow import config
from autoflow.activity_log import timestamp_now, write_log_lines
from autoflow.classification.ai_classifier import classify_with_ai
from autoflow.emails.sender import send_email
from autoflow.emails.templates import create_email_preview
from autoflow.integrations.airtable import sync_customers_to_airtable
from autoflow.integrations.exchange_rates import fetch_eur_to_usd
from autoflow.storage.database import (
    initialize_database,
    record_workflow_run,
    save_customers,
)


PROCESSED_COLUMNS = [
    "id",
    "name",
    "email",
    "message",
    "category",
    "classification_source",
    "classification_reason",
    "quote_eur",
    "quote_usd",
    "rate_date",
]


def classify_with_rules(message):
    """Classify a lowercase message using simple keyword rules."""

    if "price" in message:
        return "Sales"
    if "help" in message:
        return "Support"
    return "Other"


def review_ai_suggestion(customer, ai_result):
    """Ask a human to accept or correct the AI category."""

    suggested_category = ai_result["category"]
    classification_reason = ai_result["reason"]

    # Show the AI decision for human review
    print(f"\nAI suggestion for {customer['name']}:")
    print("Category:", suggested_category)
    print("Reason:", classification_reason)

    classification_approval = input(
        "Accept this AI category? (yes/no): "
    ).strip().lower()

    if classification_approval == "yes":
        return suggested_category, "AI Approved", classification_reason

    # Allow the user to correct the AI category
    correction = input(
        "Enter Sales, Support, or Other: "
    ).strip().title()

    if correction in {"Sales", "Support", "Other"}:
        return correction, "Human Correction", (
            f"Human changed the AI suggestion from "
            f"{suggested_category} to {correction}."
        )

    return suggested_category, "AI - Invalid Correction", (
        classification_reason + " The human correction was invalid."
    )


def process_customers(exchange_rate, rate_date, interactive=True):
    """Read, classify and enrich every customer in the input CSV."""

    processed_customers = []

    with config.INPUT_CSV_PATH.open("r", newline="", encoding="utf-8") as file:
        for customer in csv.DictReader(file):
            # Keep the original message for AI and a lowercase copy for rules
            original_message = customer["message"].strip()

            # Ask AI for a category when AI classification is enabled
            ai_result = classify_with_ai(original_message)

            if ai_result is not None and interactive:
                category, classification_source, classification_reason = (
                    review_ai_suggestion(customer, ai_result)
                )
            elif ai_result is not None:
                # Nobody is available to review: keep it visibly unreviewed
                category = ai_result["category"]
                classification_source = "AI Pending Review"
                classification_reason = ai_result["reason"]
            else:
                # Use the original keyword rules as a safe fallback
                category = classify_with_rules(original_message.lower())
                classification_source = "Rules"
                classification_reason = "Classified using keyword rules."

            print(
                customer["name"],
                "→",
                category,
                f"({classification_source})",
            )
            print("  Reason:", classification_reason)

            customer["category"] = category
            customer["classification_source"] = classification_source
            customer["classification_reason"] = classification_reason

            customer["quote_eur"] = ""
            customer["quote_usd"] = ""
            customer["rate_date"] = ""

            # Generate a converted quote only for Sales enquiries
            if category == "Sales" and exchange_rate is not None:
                customer["quote_eur"] = "100.00"
                customer["quote_usd"] = f"{100 * exchange_rate:.2f}"
                customer["rate_date"] = rate_date

            processed_customers.append(customer)

    return processed_customers


def save_processed_csv(processed_customers):
    """Save the processed customer records into a new CSV file."""

    with config.PROCESSED_CSV_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=PROCESSED_COLUMNS)
        writer.writeheader()
        writer.writerows(processed_customers)

    print("Results saved to:", config.PROCESSED_CSV_PATH)


def write_email_previews(processed_customers):
    """Generate personalized email previews without contacting customers."""

    email_previews = []

    with config.EMAIL_PREVIEWS_PATH.open("w", encoding="utf-8") as file:
        for customer in processed_customers:
            email_preview = create_email_preview(customer)
            email_previews.append(email_preview)

            file.write(f"To: {email_preview['to']}\n")
            file.write(f"Subject: {email_preview['subject']}\n")
            file.write(f"{email_preview['body']}\n")
            file.write("-" * 60 + "\n")

    print("Email previews saved to:", config.EMAIL_PREVIEWS_PATH)
    return email_previews


def review_and_send_email(email_previews):
    """Let a human pick, inspect and approve one test email.

    Returns audit entries describing the approved, rejected or failed
    email decision.
    """

    email_audit_entries = []

    # Display available email previews for human selection
    print("\nAvailable email previews:")

    for number, preview in enumerate(email_previews, start=1):
        print(f"{number}. {preview['to']} — {preview['subject']}")

    selection = input(
        "Enter the preview number you want to test: "
    ).strip()

    try:
        selected_index = int(selection) - 1
    except ValueError:
        print("Email sending skipped: enter a valid number.")
        return email_audit_entries

    if selected_index < 0 or selected_index >= len(email_previews):
        print("Email sending skipped: invalid selection.")
        return email_audit_entries

    selected_preview = email_previews[selected_index]

    # Show the complete message before requesting approval
    print("\n--- EMAIL PREVIEW ---")
    print("Original recipient:", selected_preview["to"])
    print("Subject:", selected_preview["subject"])
    print(selected_preview["body"])

    approval = input(
        "\nApprove sending this to your test Gmail? (yes/no): "
    ).strip().lower()

    if approval == "yes":
        email_sent = send_email(selected_preview)
        email_status = "EMAIL_SENT" if email_sent else "EMAIL_FAILED"
    else:
        print("Email sending skipped.")
        email_status = "EMAIL_REJECTED"

    email_audit_entries.append({
        "status": email_status,
        "recipient": selected_preview["to"],
    })

    return email_audit_entries


def write_activity_log(processed_customers, email_audit_entries):
    """Append a timestamped record of email decisions and enquiries."""

    timestamp = timestamp_now()
    lines = []

    # Record the approved, rejected or failed email decision
    for email_event in email_audit_entries:
        lines.append(
            f"{timestamp} | EMAIL | {email_event['status']} | "
            f"Recipient: {email_event['recipient']}"
        )

    for customer in processed_customers:
        lines.append(
            f"{timestamp} | ID: {customer['id']} | "
            f"Category: {customer['category']}"
        )

    write_log_lines(lines)
    print("Activity log saved.")


def run(interactive=True):
    """Execute the complete AutoFlow workflow once.

    Returns a summary of the run. With interactive=False no terminal input
    is requested and the human-approval email step is skipped.
    """

    exchange_rate, rate_date = fetch_eur_to_usd()

    processed_customers = process_customers(
        exchange_rate, rate_date, interactive
    )

    # Create the database and save all processed customer records
    initialize_database()
    save_customers(processed_customers)

    save_processed_csv(processed_customers)

    email_previews = write_email_previews(processed_customers)

    if interactive:
        email_audit_entries = review_and_send_email(email_previews)
    else:
        print("Email review skipped: no human reviewer available.")
        email_audit_entries = []

    # Synchronize processed customers with the Airtable CRM
    sync_customers_to_airtable(processed_customers)

    write_activity_log(processed_customers, email_audit_entries)

    # Record a summary of this completed workflow execution
    ai_was_used = any(
        customer["classification_source"] != "Rules"
        for customer in processed_customers
    )

    run_id = record_workflow_run(
        customer_count=len(processed_customers),
        ai_enabled=str(ai_was_used).lower(),
        status="SUCCESS",
    )

    return {
        "run_id": run_id,
        "customer_count": len(processed_customers),
        "ai_enabled": ai_was_used,
        "categories": {
            category: sum(
                customer["category"] == category
                for customer in processed_customers
            )
            for category in ("Sales", "Support", "Other")
        },
        "emails": email_audit_entries,
    }


if __name__ == "__main__":
    run()
