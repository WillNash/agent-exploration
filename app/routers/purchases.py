from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.models import row_to_dict

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


class PurchaseItemIn(BaseModel):
    product_id: int
    quantity: int


class PurchaseIn(BaseModel):
    customer_email: str
    items: list[PurchaseItemIn]


@router.get("/{customer_id}")
async def get_purchases(
    customer_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
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
            customer_id,
        )
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
async def create_purchase(
    body: PurchaseIn,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        customer = await conn.fetchrow(
            "SELECT id FROM customers WHERE email = $1", body.customer_email
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        customer_id: int = customer["id"]
        order_rows: list[dict[str, Any]] = []

        async with conn.transaction():
            for item in body.items:
                product = await conn.fetchrow(
                    "SELECT id, name, price, stock_qty FROM products WHERE id = $1 FOR UPDATE",
                    item.product_id,
                )
                if product is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Product {item.product_id} not found",
                    )
                if product["stock_qty"] < item.quantity:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Insufficient stock for '{product['name']}'",
                    )

                await conn.execute(
                    "UPDATE products SET stock_qty = stock_qty - $1 WHERE id = $2",
                    item.quantity,
                    item.product_id,
                )
                purchase_row = await conn.fetchrow(
                    """
                    INSERT INTO customer_purchases (customer_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    RETURNING *
                    """,
                    customer_id,
                    item.product_id,
                    item.quantity,
                )
                order_rows.append(
                    {
                        "purchase_id": purchase_row["id"],
                        "product_id": item.product_id,
                        "product_name": product["name"],
                        "quantity": item.quantity,
                        "unit_price": float(product["price"]),
                        "line_total": float(product["price"]) * item.quantity,
                    }
                )

    total = sum(r["line_total"] for r in order_rows)
    return {
        "customer_id": customer_id,
        "customer_email": body.customer_email,
        "items": order_rows,
        "order_total": round(total, 2),
    }
