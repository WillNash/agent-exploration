from __future__ import annotations

import json
from decimal import Decimal
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

_HELP = {
    "supported_actions": [
        {
            "action": "list_categories",
            "params": {},
        },
        {
            "action": "browse_products",
            "params": {"category": "optional string", "max_price": "optional number"},
        },
        {
            "action": "get_product",
            "params": {"product_id": "integer"},
        },
        {
            "action": "create_customer",
            "params": {"name": "string", "email": "string"},
        },
        {
            "action": "checkout",
            "params": {
                "customer_email": "string",
                "items": [{"product_id": "integer", "quantity": "integer"}],
            },
        },
        {
            "action": "list_purchases",
            "params": {"customer_email": "string"},
        },
    ]
}


def _serialise(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _row(record: asyncpg.Record) -> dict[str, Any]:
    return {k: _serialise(v) for k, v in dict(record).items()}


class GardenStoreExecutor(AgentExecutor):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        text = context.get_user_input()
        intent: Intent = parse_intent(text)
        result = await self._dispatch(intent)
        # Simple pattern: enqueue a single Message and return.
        # No Task lifecycle needed for this synchronous deterministic agent.
        await event_queue.enqueue_event(new_text_message(json.dumps(result)))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancellation is not supported")

    async def _dispatch(self, intent: Intent) -> Any:
        match intent:
            case ListCategoriesIntent():
                return await self._list_categories()
            case BrowseProductsIntent():
                return await self._browse_products(intent)
            case GetProductIntent():
                return await self._get_product(intent)
            case CreateCustomerIntent():
                return await self._create_customer(intent)
            case CheckoutIntent():
                return await self._checkout(intent)
            case ListPurchasesIntent():
                return await self._list_purchases(intent)
            case UnknownIntent():
                return {"error": "unknown_intent", "help": _HELP}

    async def _list_categories(self) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT category FROM products "
                "WHERE category IS NOT NULL ORDER BY category"
            )
        return [r["category"] for r in rows]

    async def _browse_products(self, intent: BrowseProductsIntent) -> list[dict[str, Any]]:
        query = "SELECT * FROM products WHERE 1=1"
        args: list[Any] = []

        if intent.category is not None:
            args.append(intent.category)
            query += f" AND category = ${len(args)}"

        if intent.max_price is not None:
            args.append(intent.max_price)
            query += f" AND price <= ${len(args)}"

        query += " ORDER BY category, name"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)

        return [_row(r) for r in rows]

    async def _get_product(self, intent: GetProductIntent) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM products WHERE id = $1", intent.product_id
            )
        if row is None:
            return {"error": "product_not_found", "product_id": intent.product_id}
        return _row(row)

    async def _create_customer(self, intent: CreateCustomerIntent) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO customers (name, email)
                VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE
                    SET name = EXCLUDED.name
                RETURNING *
                """,
                intent.name,
                intent.email,
            )
        return _row(row)

    async def _checkout(self, intent: CheckoutIntent) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            customer = await conn.fetchrow(
                "SELECT id FROM customers WHERE email = $1", intent.customer_email
            )
            if customer is None:
                return {
                    "error": "customer_not_found",
                    "email": intent.customer_email,
                    "hint": "Call create_customer first with {action: create_customer, name, email}",
                }

            customer_id: int = customer["id"]
            order_rows: list[dict[str, Any]] = []

            async with conn.transaction():
                for item in intent.items:
                    product = await conn.fetchrow(
                        "SELECT id, name, price, stock_qty FROM products "
                        "WHERE id = $1 FOR UPDATE",
                        item.product_id,
                    )
                    if product is None:
                        return {"error": "product_not_found", "product_id": item.product_id}
                    if product["stock_qty"] < item.quantity:
                        return {
                            "error": "insufficient_stock",
                            "product": product["name"],
                            "requested": item.quantity,
                            "available": product["stock_qty"],
                        }

                    await conn.execute(
                        "UPDATE products SET stock_qty = stock_qty - $1 WHERE id = $2",
                        item.quantity,
                        item.product_id,
                    )
                    purchase = await conn.fetchrow(
                        """
                        INSERT INTO customer_purchases (customer_id, product_id, quantity)
                        VALUES ($1, $2, $3)
                        RETURNING id
                        """,
                        customer_id,
                        item.product_id,
                        item.quantity,
                    )
                    order_rows.append(
                        {
                            "purchase_id": purchase["id"],
                            "product_id": item.product_id,
                            "product_name": product["name"],
                            "quantity": item.quantity,
                            "unit_price": float(product["price"]),
                            "line_total": float(product["price"]) * item.quantity,
                        }
                    )

        total = sum(r["line_total"] for r in order_rows)
        return {
            "status": "confirmed",
            "customer_email": intent.customer_email,
            "items": order_rows,
            "order_total": round(total, 2),
        }

    async def _list_purchases(self, intent: ListPurchasesIntent) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            customer = await conn.fetchrow(
                "SELECT id FROM customers WHERE email = $1", intent.customer_email
            )
            if customer is None:
                return []

            rows = await conn.fetch(
                """
                SELECT
                    cp.id,
                    cp.customer_id,
                    cp.product_id,
                    p.name  AS product_name,
                    p.price AS price,
                    cp.quantity,
                    cp.purchased_at
                FROM customer_purchases cp
                JOIN products p ON p.id = cp.product_id
                WHERE cp.customer_id = $1
                ORDER BY cp.purchased_at DESC
                """,
                customer["id"],
            )
        return [_row(r) for r in rows]
