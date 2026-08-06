from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.models import row_to_dict

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str
    email: str


@router.get("/lookup")
async def lookup_customer(
    email: str,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM customers WHERE email = $1", email)
    if row is None:
        raise HTTPException(status_code=404, detail="customer_not_found")
    return row_to_dict(row)


@router.get("")
async def list_customers(
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM customers ORDER BY name")
    return [row_to_dict(r) for r in rows]


@router.post("", status_code=201)
async def upsert_customer(
    body: CustomerIn,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO customers (name, email)
            VALUES ($1, $2)
            ON CONFLICT (email) DO UPDATE
                SET name = EXCLUDED.name
            RETURNING *
            """,
            body.name,
            body.email,
        )
    return row_to_dict(row)
