"""Customer records, always scoped to one workspace."""

from sqlalchemy import select

from autoflow.storage.models import Customer


CUSTOMER_FIELDS = (
    "customer_id",
    "name",
    "message",
    "category",
    "classification_source",
    "classification_reason",
    "quote_eur",
    "quote_usd",
    "rate_date",
)


def save_customers(session, workspace_id, customers):
    """Insert new customers or update existing ones using their email."""

    for record in customers:
        email = record["email"].strip().lower()
        values = {
            "customer_id": record["id"],
            **{field: record[field] for field in CUSTOMER_FIELDS[1:]},
        }

        customer = get_customer_by_email(session, workspace_id, email)

        if customer is None:
            session.add(Customer(workspace_id=workspace_id, email=email, **values))
        else:
            for field, value in values.items():
                setattr(customer, field, value)

    session.flush()
    print(f"Database synchronized: {len(customers)} customers.")


def list_customers(session, workspace_id, category=None):
    query = select(Customer).where(Customer.workspace_id == workspace_id)

    if category is not None:
        query = query.where(Customer.category == category)

    return session.scalars(query.order_by(Customer.id)).all()


def get_customer(session, workspace_id, customer_row_id):
    return session.scalar(
        select(Customer).where(
            Customer.workspace_id == workspace_id,
            Customer.id == customer_row_id,
        )
    )


def get_customer_by_email(session, workspace_id, email):
    return session.scalar(
        select(Customer).where(
            Customer.workspace_id == workspace_id,
            Customer.email == email.strip().lower(),
        )
    )


def update_customer_classification(
    session, workspace_id, email, category, source, reason
):
    """Store a human-reviewed category for an existing customer.

    Quotes only apply to Sales enquiries, so they are cleared otherwise.
    """

    customer = get_customer_by_email(session, workspace_id, email)

    if customer is None:
        return None

    customer.category = category
    customer.classification_source = source
    customer.classification_reason = reason

    if category != "Sales":
        customer.quote_eur = ""
        customer.quote_usd = ""
        customer.rate_date = ""

    session.flush()
    return customer
