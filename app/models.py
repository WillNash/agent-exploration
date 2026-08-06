from __future__ import annotations

from decimal import Decimal
from typing import Any

from typing_extensions import TypedDict


class Product(TypedDict):
    id: int
    name: str
    description: str | None
    price: float
    category: str | None
    stock_qty: int


class Customer(TypedDict):
    id: int
    name: str
    email: str
    created_at: str


class PurchaseItem(TypedDict):
    id: int
    customer_id: int
    product_id: int
    product_name: str
    price: float
    quantity: int
    purchased_at: str


def row_to_dict(row: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result
