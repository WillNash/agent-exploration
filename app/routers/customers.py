from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.models import row_to_dict
from app.services import get_customer_by_email, upsert_customer

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str
    email: str


@router.get("/lookup")
async def lookup_customer(
    email: str,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    customer = await get_customer_by_email(pool, email)
    if customer is None:
        raise HTTPException(status_code=404, detail="customer_not_found")
    return customer


@router.get("")
async def list_customers(
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM customers ORDER BY name")
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
async def upsert_customer_route(
    body: CustomerIn,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    return await upsert_customer(pool, name=body.name, email=body.email)
