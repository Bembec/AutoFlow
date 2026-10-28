"""
Tests Luphina's connection to Airtable without creating or changing records.
"""

import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote


# Load the private settings stored in .env
load_dotenv()

token = os.getenv("AIRTABLE_TOKEN")
base_id = os.getenv("AIRTABLE_BASE_ID")
table_name = os.getenv("AIRTABLE_TABLE_NAME")

if not token or not base_id or not table_name:
    print("Missing Airtable configuration in .env")
else:
    encoded_table_name = quote(table_name, safe="")
    url = f"https://api.airtable.com/v0/{base_id}/{encoded_table_name}"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        print("Airtable connection successful!")
        print("Records currently found:", len(data["records"]))

    except (requests.RequestException, ValueError, KeyError) as error:
        print("Airtable connection failed:", error)