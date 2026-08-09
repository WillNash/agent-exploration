from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.database import get_pool

router = APIRouter()


@router.get("/health")
async def health(pool: asyncpg.Pool = Depends(get_pool)) -> JSONResponse:
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return JSONResponse({"status": "ok", "db": "connected"})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
