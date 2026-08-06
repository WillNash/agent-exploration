from __future__ import annotations

import json
from typing import Any

import asyncpg

from a2a.helpers.proto_helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from app.agent.intents import (
    BrowseProductsIntent,
    CheckoutIntent,
    CreateCustomerIntent,
    GetProductIntent,
    Intent,
    ListCategoriesIntent,
    ListPurchasesIntent,
    UnknownIntent,
    parse_intent,
)
from app.services import (
    CheckoutItem,
    CustomerNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
    browse_products,
    checkout,
    get_customer_by_email,
    get_product,
    list_categories,
    list_purchases,
    upsert_customer,
)

_HELP = {
    "supported_actions": [
        {"action": "list_categories", "params": {}},
        {"action": "browse_products", "params": {"category": "optional string", "max_price": "optional number"}},
        {"action": "get_product", "params": {"product_id": "integer"}},
        {"action": "create_customer", "params": {"name": "string", "email": "string"}},
        {
            "action": "checkout",
            "params": {
                "customer_email": "string",
                "items": [{"product_id": "integer", "quantity": "integer"}],
            },
        },
        {"action": "list_purchases", "params": {"customer_email": "string"}},
    ]
}


class GardenStoreExecutor(AgentExecutor):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        text = context.get_user_input()
        intent: Intent = parse_intent(text)
        result = await self._dispatch(intent)
        await event_queue.enqueue_event(new_text_message(json.dumps(result)))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancellation is not supported")

    async def _dispatch(self, intent: Intent) -> Any:
        match intent:
            case ListCategoriesIntent():
                return await list_categories(self._pool)
            case BrowseProductsIntent():
                return await browse_products(
                    self._pool,
                    category=intent.category,
                    max_price=intent.max_price,
                )
            case GetProductIntent():
                product = await get_product(self._pool, intent.product_id)
                if product is None:
                    return {"error": "product_not_found", "product_id": intent.product_id}
                return product
            case CreateCustomerIntent():
                return await upsert_customer(self._pool, name=intent.name, email=intent.email)
            case CheckoutIntent():
                return await self._checkout(intent)
            case ListPurchasesIntent():
                return await self._list_purchases(intent)
            case UnknownIntent():
                return {"error": "unknown_intent", "help": _HELP}

    async def _checkout(self, intent: CheckoutIntent) -> dict[str, Any]:
        try:
            return await checkout(
                self._pool,
                customer_email=intent.customer_email,
                items=[
                    CheckoutItem(product_id=i.product_id, quantity=i.quantity)
                    for i in intent.items
                ],
            )
        except CustomerNotFoundError as e:
            return {
                "error": "customer_not_found",
                "email": e.email,
                "hint": "Call create_customer first with {action: create_customer, name, email}",
            }
        except ProductNotFoundError as e:
            return {"error": "product_not_found", "product_id": e.product_id}
        except InsufficientStockError as e:
            return {
                "error": "insufficient_stock",
                "product": e.product_name,
                "requested": e.requested,
                "available": e.available,
            }

    async def _list_purchases(self, intent: ListPurchasesIntent) -> list[dict[str, Any]]:
        customer = await get_customer_by_email(self._pool, intent.customer_email)
        if customer is None:
            return []
        return await list_purchases(self._pool, customer["id"])
