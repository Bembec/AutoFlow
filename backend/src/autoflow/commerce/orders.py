"""
Turn store order data into a normalised order.

Understands Shopify order webhooks (orders/create, orders/paid) and a
simple generic shape, so other stores can send orders too:

    {"order_id": "1001", "customer_name": "Ada", "customer_email": "ada@example.com",
     "currency": "EUR", "tax": "4.00",
     "items": [{"title": "Mug", "quantity": 2, "unit_price": "10.00"}]}
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation


class OrderError(ValueError):
    """The order data is missing something an invoice needs."""


@dataclass
class Order:
    external_ref: str
    customer_name: str
    customer_email: str
    currency: str
    lines: list[dict] = field(default_factory=list)
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    checkout_token: str | None = None


def money(value, what="amount"):
    try:
        return Decimal(str(value if value not in (None, "") else "0")).quantize(Decimal("0.01"))
    except InvalidOperation as error:
        raise OrderError(f"Invalid {what}: {value!r}") from error


def parse_order(data):
    if not isinstance(data, dict):
        raise OrderError("Order data must be an object.")

    if "line_items" in data:
        return _shopify(data)
    if "items" in data:
        return _generic(data)

    raise OrderError("Order data has no line_items (Shopify) or items.")


def _shopify(data):
    customer = data.get("customer") or {}
    name = " ".join(filter(None, [customer.get("first_name"), customer.get("last_name")]))
    billing = data.get("billing_address") or {}

    lines = []
    for item in data["line_items"]:
        quantity = int(item.get("quantity") or 1)
        unit = money(item.get("price"), "price")
        lines.append({
            "title": str(item.get("title") or item.get("name") or "Item"),
            "quantity": quantity,
            "unit_price": str(unit),
            "amount": str(unit * quantity),
        })

    subtotal = money(data.get("subtotal_price")) or sum((Decimal(line["amount"]) for line in lines), Decimal("0"))
    tax = money(data.get("total_tax"))
    total = money(data.get("total_price")) or subtotal + tax

    order_id = data.get("id") or data.get("order_number")
    if not order_id:
        raise OrderError("Shopify order has no id.")

    return Order(
        external_ref=str(order_id),
        customer_name=name or str(billing.get("name") or ""),
        customer_email=str(data.get("email") or customer.get("email") or ""),
        currency=str(data.get("currency") or "USD").upper()[:3],
        lines=lines,
        subtotal=subtotal,
        tax=tax,
        total=total,
        checkout_token=data.get("checkout_token"),
    )


def _generic(data):
    if not data.get("order_id"):
        raise OrderError("Order data needs an order_id.")

    lines = []
    for item in data["items"]:
        quantity = int(item.get("quantity") or 1)
        unit = money(item.get("unit_price"), "unit_price")
        lines.append({
            "title": str(item.get("title") or "Item"),
            "quantity": quantity,
            "unit_price": str(unit),
            "amount": str(unit * quantity),
        })

    subtotal = sum((Decimal(line["amount"]) for line in lines), Decimal("0"))
    tax = money(data.get("tax"))

    return Order(
        external_ref=str(data["order_id"]),
        customer_name=str(data.get("customer_name") or ""),
        customer_email=str(data.get("customer_email") or ""),
        currency=str(data.get("currency") or "USD").upper()[:3],
        lines=lines,
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        checkout_token=data.get("checkout_token"),
    )
