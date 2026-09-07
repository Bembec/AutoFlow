"""
Creates one test customer record in Airtable through the API.
Run this file only once to avoid creating duplicates.
"""

import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote


load_dotenv()

token = os.getenv("AIRTABLE_TOKEN")
base_id = os.getenv("AIRTABLE_BASE_ID")
table_name = os.getenv("AIRTABLE_TABLE_NAME")

encoded_table_name = quote(table_name, safe="")
url = f"https://api.airtable.com/v0/{base_id}/{encoded_table_name}"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

customer_data = {
    "fields": {
        "Name": "Ada",
        "Email": "ada@example.com",
        "Message": "I want to know your price",
        "Category": "Sales",
    },
    "typecast": True,
}

try:
    # First, retrieve existing Airtable records
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    existing_records = response.json()["records"]

    customer_email = customer_data["fields"]["Email"].strip().lower()

    # Check whether the email already exists
    duplicate_found = any(
        record.get("fields", {}).get("Email", "").strip().lower()
        == customer_email
        for record in existing_records
    )

    if duplicate_found:
        print("Duplicate detected. Record was not created:", customer_email)

    else:
        # Create the record only when no matching email exists
        response = requests.post(
            url,
            headers=headers,
            json=customer_data,
            timeout=30,
        )
        response.raise_for_status()
        created_record = response.json()

        print("Record created successfully!")
        print("Airtable record ID:", created_record["id"])

except requests.HTTPError as error:
    print("Airtable rejected the request:")
    print(error.response.text)

except requests.RequestException as error:
    print("Connection problem:", error)

except (ValueError, KeyError) as error:
    print("Response-processing problem:", error)