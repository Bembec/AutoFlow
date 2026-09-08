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


## Version 4 — Controlled Email Automation

- Generates personalized customer email responses.
- Allows a human to inspect and approve each message.
- Sends controlled test emails through Gmail.
- Uses an environment safety switch to prevent accidental sending.
- Records sent, rejected and failed email attempts in the activity log.

## Version 5 — AI-Assisted Classification

- Uses the Gemini API to classify enquiries as Sales, Support or Other.
- Generates a short explanation for each classification.
- Requires human approval or correction of AI decisions.
- Uses keyword rules when AI is disabled or unavailable.
- Includes a safety switch to control API usage.
- Uses only fake customer data during free-tier development.

## Version 6 — Database Persistence

- Stores processed customers in SQLite.
- Inserts new customers and updates existing customers by email.
- Prevents duplicate customer records.
- Records timestamped workflow execution history.
- Provides database retrieval functions for the future API and dashboard.

> During development, customer emails are redirected to a test Gmail account.
> Gmail credentials are stored privately in `.env` and are never committed.

## Installation

Create and activate a virtual environment, then install the required packages:

```bash
pip install -r requirements.txt