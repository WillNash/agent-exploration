from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_user
from app.database import get_pool
from app.services import (
    CheckoutItem,
    InsufficientStockError,
    ProductNotFoundError,
    checkout,
    list_purchases,
)

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


class PurchaseItemIn(BaseModel):
    product_id: int
    quantity: int


class PurchaseIn(BaseModel):
    items: list[PurchaseItemIn]


@router.get("/mine")
async def get_my_purchases(
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(require_user),
) -> list[dict[str, Any]]:
    return await list_purchases(pool, int(user["sub"]))


@router.get("/{customer_id}")
async def get_purchases(
    customer_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    return await list_purchases(pool, customer_id)


@router.post("", status_code=201)
async def create_purchase(
    body: PurchaseIn,
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    try:
        return await checkout(
            pool,
            customer_id=int(user["sub"]),
            items=[CheckoutItem(product_id=i.product_id, quantity=i.quantity) for i in body.items],
        )
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Product {e.product_id} not found")
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail=f"Insufficient stock for '{e.product_name}'")
