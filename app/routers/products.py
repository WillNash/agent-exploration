from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_pool
from app.models import row_to_dict

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(
    category: str | None = Query(default=None),
    max_price: float | None = Query(default=None),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    query = "SELECT * FROM products WHERE 1=1"
    args: list[Any] = []

    if category is not None:
        args.append(category)
        query += f" AND category = ${len(args)}"

    if max_price is not None:
        args.append(max_price)
        query += f" AND price <= ${len(args)}"

    query += " ORDER BY category, name"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)

    return [row_to_dict(r) for r in rows]


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM products WHERE id = $1", product_id
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return row_to_dict(row)
