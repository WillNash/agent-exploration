from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.auth import current_user
from app.database import get_pool
from app.models import row_to_dict
from app.services import get_customer_by_id

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _require_auth() -> dict[str, Any]:
    user = current_user.get()
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user


@router.get("/me")
async def get_me(
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(_require_auth),
) -> dict[str, Any]:
    customer = await get_customer_by_id(pool, int(user["sub"]))
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
