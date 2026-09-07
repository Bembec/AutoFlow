"""
AutoFlow AI — Business Workflow Automation System

This program reads customer enquiries from a CSV file, categorizes them,
retrieves a EUR-to-USD exchange rate, generates sample sales quotes,
saves the processed records, and logs its activity.

Future versions will connect to Airtable, prevent duplicate records,
use AI for classification, and automate business follow-ups.
"""

import csv
import requests
from pathlib import Path
from datetime import datetime
import os
from urllib.parse import quote
from dotenv import load_dotenv

# Load the private Airtable configuration from .env
load_dotenv()

airtable_token = os.getenv("AIRTABLE_TOKEN")
airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
airtable_table_name = os.getenv("AIRTABLE_TABLE_NAME")

def log_airtable_event(status, email="-", details=""):
    """Append an Airtable synchronization event to the activity log."""

    log_path = Path(__file__).parent / "activity.log"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

    with log_path.open("a", encoding="utf-8") as log:
        log.write(
            f"{timestamp} | AIRTABLE | {status} | "
            f"Email: {email} | Details: {details}\n"
        )

def log_airtable_event(status, email="-", details=""):
    """Append an Airtable synchronization event to the activity log."""

    log_path = Path(__file__).parent / "activity.log"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

    with log_path.open("a", encoding="utf-8") as log:
        log.write(
            f"{timestamp} | AIRTABLE | {status} | "
            f"Email: {email} | Details: {details}\n"
        )


def sync_customers_to_airtable(customers):
    """Create new Airtable records or update existing ones using email."""

    # Stop safely if any Airtable configuration value is missing
    if not all([
        airtable_token,
        airtable_base_id,
        airtable_table_name,
    ]):
        print("Airtable sync skipped: configuration is missing.")
        log_airtable_event(
            "CONFIGURATION_MISSING",
            details="Check the .env file.",
        )
        return

    encoded_table_name = quote(airtable_table_name, safe="")

    airtable_url = (
        f"https://api.airtable.com/v0/"
        f"{airtable_base_id}/{encoded_table_name}"
    )

    headers = {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json",
    }

    try:
        # Store existing customers from every Airtable page
        existing_customers = {}
        request_parameters = {"pageSize": 100}

        while True:
            # GET retrieves one page of existing Airtable records
            response = requests.get(
                airtable_url,
                headers=headers,
                params=request_parameters,
                timeout=30,
            )
            response.raise_for_status()
            airtable_data = response.json()

            for record in airtable_data["records"]:
                fields = record.get("fields", {})
                existing_email = (
                    fields.get("Email", "").strip().lower()
                )

                if existing_email:
                    existing_customers[existing_email] = record

            # Airtable provides an offset when another page exists
            next_offset = airtable_data.get("offset")

            if not next_offset:
                break

            request_parameters["offset"] = next_offset

        print(
            "Existing Airtable customers checked:",
            len(existing_customers),
        )

    except (requests.RequestException, ValueError, KeyError) as error:
        print("Could not check existing Airtable records:", error)
        log_airtable_event("READ_FAILED", details=str(error))
        return

    for customer in customers:
        # Clean important customer fields before validation
        name = customer["name"].strip()
        email = customer["email"].strip().lower()
        message = customer["message"].strip()

        # Skip records with missing required information
        if not name or not email or not message:
            print("Invalid customer skipped: required information is missing.")
            log_airtable_event(
                "VALIDATION_FAILED",
                email,
                "Required information is missing.",
            )
            continue

        # Perform a simple email-format check
        if "@" not in email or "." not in email.split("@")[-1]:
            print("Invalid email skipped:", email)
            log_airtable_event("INVALID_EMAIL", email)
            continue

        # Prepare the cleaned customer information for Airtable
        customer_data = {
            "fields": {
                "Name": name,
                "Email": email,
                "Message": message,
                "Category": customer["category"],
            },
            "typecast": True,
        }

        if email in existing_customers:
            existing_record = existing_customers[email]
            current_fields = existing_record.get("fields", {})
            new_fields = customer_data["fields"]

            # Check whether any customer information has changed
            information_changed = any(
                current_fields.get(field) != value
                for field, value in new_fields.items()
            )

            if not information_changed:
                print("Airtable record unchanged:", email)
                log_airtable_event("UNCHANGED", email)
                continue

            record_id = existing_record["id"]
            update_url = f"{airtable_url}/{record_id}"

            try:
                # PATCH modifies the existing record instead of creating another
                response = requests.patch(
                    update_url,
                    headers=headers,
                    json=customer_data,
                    timeout=30,
                )
                response.raise_for_status()

                existing_customers[email] = response.json()

                print("Updated in Airtable:", email)
                log_airtable_event("UPDATED", email)

            except requests.RequestException as error:
                print("Could not update Airtable customer:", email, error)
                log_airtable_event(
                    "UPDATE_FAILED",
                    email,
                    str(error),
                )

            continue

        try:
            # POST creates a record because this email does not exist
            response = requests.post(
                airtable_url,
                headers=headers,
                json=customer_data,
                timeout=30,
            )
            response.raise_for_status()

            created_record = response.json()
            existing_customers[email] = created_record

            print("Added to Airtable:", email)
            log_airtable_event("CREATED", email)

        except requests.RequestException as error:
            print("Could not add customer to Airtable:", email, error)
            log_airtable_event(
                "CREATE_FAILED",
                email,
                str(error),
            )
            
# Retrieve the latest EUR-to-USD reference rate from an external API
exchange_rate = None
rate_date = None

url = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD"

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    exchange_rate = data["rates"]["USD"]
    rate_date = data["date"]

    print(f"Reference rate: 1 EUR = {exchange_rate} USD")
    print("Rate date:", rate_date)

except (requests.RequestException, ValueError, KeyError) as error:
    print("Exchange rate unavailable:", error)
    print("Customer categorization will continue without quotes.")


# Read and process customer enquiries from the input CSV file
file_path = Path(__file__).parent / "customers.csv"
processed_customers = []

with file_path.open("r", newline="", encoding="utf-8") as file:
    customers = csv.DictReader(file)

    for customer in customers:
        message = customer["message"].lower()

        # Categorize each enquiry using simple keyword rules
        if "price" in message:
            category = "Sales"
        elif "help" in message:
            category = "Support"
        else:
            category = "Other"

        print(customer["name"], "→", category)

        customer["category"] = category
        customer["quote_eur"] = ""
        customer["quote_usd"] = ""
        customer["rate_date"] = ""

        # Generate a sample converted quote only for Sales enquiries
        if category == "Sales" and exchange_rate is not None:
            customer["quote_eur"] = "100.00"
            customer["quote_usd"] = f"{100 * exchange_rate:.2f}"
            customer["rate_date"] = rate_date

        processed_customers.append(customer)


# Save the updated customer records into a new CSV file
output_path = Path(__file__).parent / "processed_customers.csv"

with output_path.open("w", newline="", encoding="utf-8") as file:
    columns = [
        "id",
        "name",
        "email",
        "message",
        "category",
        "quote_eur",
        "quote_usd",
        "rate_date",
    ]

    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(processed_customers)

print("Results saved to:", output_path)

# Synchronize processed customers with the Airtable CRM
sync_customers_to_airtable(processed_customers)


# Append a timestamped record of each processed enquiry to the activity log
log_path = Path(__file__).parent / "activity.log"
timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

with log_path.open("a", encoding="utf-8") as log:
    for customer in processed_customers:
        log.write(
            f"{timestamp} | ID: {customer['id']} | "
            f"Category: {customer['category']}\n"
        )

print("Activity log saved.")