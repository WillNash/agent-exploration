from __future__ import annotations

import asyncpg
from fastapi import Request

_pool: asyncpg.Pool | None = None


def set_app_pool(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool


def get_app_pool() -> asyncpg.Pool | None:
    return _pool


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=2, max_size=10)


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool
