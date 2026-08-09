from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class BrowseProductsIntent:
    category: str | None
    max_price: float | None


@dataclass(slots=True, frozen=True)
class GetProductIntent:
    product_id: int


@dataclass(slots=True, frozen=True)
class ListCategoriesIntent:
    pass


@dataclass(slots=True, frozen=True)
class CheckoutItemIntent:
    product_id: int
    quantity: int


@dataclass(slots=True, frozen=True)
class CheckoutIntent:
    # customer_email removed — identity comes from the Bearer token
    items: tuple[CheckoutItemIntent, ...]


@dataclass(slots=True, frozen=True)
class ListPurchasesIntent:
    # customer_email removed — identity comes from the Bearer token
    pass


@dataclass(slots=True, frozen=True)
class UnknownIntent:
    raw_text: str


Intent = (
    BrowseProductsIntent
    | GetProductIntent
    | ListCategoriesIntent
    | CheckoutIntent
    | ListPurchasesIntent
    | UnknownIntent
)


def parse_intent(text: str) -> Intent:
    try:
        data: dict[str, Any] = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return UnknownIntent(raw_text=text)

    action = data.get("action")

    match action:
        case "browse_products":
            return BrowseProductsIntent(
                category=data.get("category"),
                max_price=float(data["max_price"]) if "max_price" in data else None,
            )
        case "get_product":
            if "product_id" not in data:
                return UnknownIntent(raw_text=text)
            return GetProductIntent(product_id=int(data["product_id"]))
        case "list_categories":
            return ListCategoriesIntent()
        case "checkout":
            if "items" not in data:
                return UnknownIntent(raw_text=text)
            return CheckoutIntent(
                items=tuple(
                    CheckoutItemIntent(
                        product_id=int(i["product_id"]),
                        quantity=int(i["quantity"]),
                    )
                    for i in data["items"]
                ),
            )
        case "list_purchases":
            return ListPurchasesIntent()
        case _:
            return UnknownIntent(raw_text=text)
