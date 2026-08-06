from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_pool
from app.services import browse_products, get_product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(
    category: str | None = Query(default=None),
    max_price: float | None = Query(default=None),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    return await browse_products(pool, category=category, max_price=max_price)


@router.get("/{product_id}")
async def get_product_by_id(
    product_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    product = await get_product(pool, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
