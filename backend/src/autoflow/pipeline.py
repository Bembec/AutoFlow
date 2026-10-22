"""
AutoFlow AI — Customer enquiry workflow

Reads customer enquiries from a CSV file, classifies them (AI with human
review, or keyword rules), adds EUR-to-USD sample quotes to Sales
enquiries, stores the results in SQLite and CSV, sends one approved test
email, synchronizes Airtable and records the activity.

Run with:  python -m autoflow

When run without a terminal (interactive=False, e.g. from the API), AI
suggestions and outgoing emails are queued as pending approvals that a
person decides through the API. Nothing is sent without approval.

Every run belongs to one workspace. The command line uses the "local"
workspace; the API uses the caller's workspace.
"""

import csv

from autoflow import approvals, config
from autoflow.accounts.service import ensure_local_workspace
from autoflow.activity_log import timestamp_now, write_log_lines
from autoflow.classification.ai_classifier import classify_with_ai
from autoflow.emails.sender import send_email
from autoflow.emails.templates import create_email_preview
from autoflow.integrations.airtable import sync_customers_to_airtable
from autoflow.integrations.exchange_rates import fetch_eur_to_usd
from autoflow.storage import initialize_storage
from autoflow.storage.customers import save_customers
from autoflow.storage.db import session_scope
from autoflow.storage.workflow_runs import record_workflow_run


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
    """Read, classify and enrich every customer in the input CSV.

    Returns the processed customers and the AI suggestions that still
    need a human review (only when not interactive).
    """

    processed_customers = []
    pending_reviews = []

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
                # Nobody is available to review: queue it for a human
                category = ai_result["category"]
                classification_source = "AI Pending Review"
                classification_reason = ai_result["reason"]
                pending_reviews.append((customer, ai_result))
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

    return processed_customers, pending_reviews


def save_processed_csv(processed_customers):
    """Save the processed customer records into a new CSV file."""

    with config.PROCESSED_CSV_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=PROCESSED_COLUMNS)
        writer.writeheader()
        writer.writerows(processed_customers)

    print("Results saved to:", config.PROCESSED_CSV_PATH)


def write_email_previews(email_previews):
    """Save email previews to a text file for local inspection."""

    with config.EMAIL_PREVIEWS_PATH.open("w", encoding="utf-8") as file:
        for email_preview in email_previews:
            file.write(f"To: {email_preview['to']}\n")
            file.write(f"Subject: {email_preview['subject']}\n")
            file.write(f"{email_preview['body']}\n")
            file.write("-" * 60 + "\n")

    print("Email previews saved to:", config.EMAIL_PREVIEWS_PATH)


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


def write_activity_log(workspace_id, processed_customers, email_audit_entries):
    """Append a timestamped record of email decisions and enquiries."""

    timestamp = f"{timestamp_now()} | Workspace: {workspace_id}"
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


def run_for_workspace(session, workspace_id, interactive=False, is_local=False):
    """Execute the workflow once for one workspace and return a summary.

    With interactive=False no terminal input is requested: AI suggestions
    and emails are queued as approvals. Local files (CSV, previews) and the
    .env-configured Airtable sync are only used by the local workspace, so
    one business's data never reaches another's files or CRM.
    """

    exchange_rate, rate_date = fetch_eur_to_usd()

    processed_customers, pending_reviews = process_customers(
        exchange_rate, rate_date, interactive
    )

    save_customers(session, workspace_id, processed_customers)

    for customer, ai_result in pending_reviews:
        approvals.request_classification_review(
            session, workspace_id, customer, ai_result
        )

    email_previews = [
        create_email_preview(customer) for customer in processed_customers
    ]

    if is_local:
        save_processed_csv(processed_customers)
        write_email_previews(email_previews)

    if interactive:
        email_audit_entries = review_and_send_email(email_previews)
    else:
        # Queue every email; a person approves each one through the API
        for email_preview in email_previews:
            approvals.request_email_approval(session, workspace_id, email_preview)

        print(f"Emails queued for approval: {len(email_previews)}")
        email_audit_entries = []

    if is_local:
        # Synchronize processed customers with the Airtable CRM
        sync_customers_to_airtable(processed_customers)

    write_activity_log(workspace_id, processed_customers, email_audit_entries)

    # Record a summary of this completed workflow execution
    ai_was_used = any(
        customer["classification_source"] != "Rules"
        for customer in processed_customers
    )

    run_id = record_workflow_run(
        session,
        workspace_id,
        customer_count=len(processed_customers),
        ai_enabled=ai_was_used,
        status="SUCCESS",
    )
    session.commit()

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


def run(interactive=True):
    """Run the workflow from the command line in the local workspace."""

    initialize_storage()

    with session_scope() as session:
        workspace = ensure_local_workspace(session)
        session.commit()

        return run_for_workspace(
            session, workspace.id, interactive=interactive, is_local=True
        )


if __name__ == "__main__":
    run()
