from autoflow.storage import database


def make_customer(email, category="Sales"):
    return {
        "id": "1",
        "name": "Ada",
        "email": email,
        "message": "I want to know your price",
        "category": category,
        "classification_source": "Rules",
        "classification_reason": "Classified using keyword rules.",
        "quote_eur": "",
        "quote_usd": "",
        "rate_date": "",
    }


def test_save_customers_upserts_by_email():
    database.initialize_database()

    database.save_customers([make_customer("upsert@example.com", "Sales")])
    database.save_customers([make_customer("upsert@example.com", "Support")])

    matches = [
        customer
        for customer in database.get_all_customers()
        if customer["email"] == "upsert@example.com"
    ]

    assert len(matches) == 1
    assert matches[0]["category"] == "Support"


def test_record_workflow_run():
    database.initialize_database()
    database.record_workflow_run(customer_count=4, ai_enabled="false")

    latest_run = database.get_workflow_runs(limit=1)[0]

    assert latest_run["customer_count"] == 4
    assert latest_run["status"] == "SUCCESS"
