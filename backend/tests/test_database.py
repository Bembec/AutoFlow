from autoflow.accounts.service import ensure_local_workspace
from autoflow.storage import customers as customer_store
from autoflow.storage import workflow_runs as run_store
from autoflow.storage.db import session_scope


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
    with session_scope() as session:
        workspace_id = ensure_local_workspace(session).id

        customer_store.save_customers(
            session, workspace_id, [make_customer("Upsert@Example.com", "Sales")]
        )
        customer_store.save_customers(
            session, workspace_id, [make_customer("upsert@example.com", "Support")]
        )

        customers = customer_store.list_customers(session, workspace_id)

    assert len(customers) == 1
    assert customers[0].email == "upsert@example.com"
    assert customers[0].category == "Support"


def test_record_workflow_run():
    with session_scope() as session:
        workspace_id = ensure_local_workspace(session).id
        run_store.record_workflow_run(
            session, workspace_id, customer_count=4, ai_enabled=False
        )

        latest_run = run_store.list_workflow_runs(session, workspace_id, limit=1)[0]

    assert latest_run.customer_count == 4
    assert latest_run.status == "SUCCESS"
    assert latest_run.run_timestamp.tzinfo is not None
