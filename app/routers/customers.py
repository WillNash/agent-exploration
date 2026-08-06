from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.database import get_pool
from app.models import row_to_dict

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str
    email: str


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
