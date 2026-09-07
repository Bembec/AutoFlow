# AutoFlow AI

AutoFlow AI is a developing Python business-workflow automation system.

It processes customer enquiries from CSV data, categorizes them, enriches sales enquiries with exchange-rate information, synchronizes records with Airtable, prevents duplicates, and records activity logs.

## Current Features

### Version 1 — CSV Processing

- Reads customer enquiries from `customers.csv`
- Categorizes enquiries as Sales, Support, or Other
- Saves processed records to `processed_customers.csv`
- Creates timestamped activity logs

### Version 2 — API Enrichment

- Retrieves EUR-to-USD reference rates
- Generates sample converted quotes for Sales enquiries
- Continues processing safely if the API is unavailable

### Version 3 — Airtable Integration

- Authenticates using a Personal Access Token
- Creates Airtable records with `POST`
- Updates changed records with `PATCH`
- Prevents duplicate customers using email addresses
- Validates required fields and email format
- Supports Airtable pagination
- Logs created, updated, unchanged, and failed operations

## Installation

Create and activate a virtual environment, then install the required packages:

```bash
pip install -r requirements.txt
