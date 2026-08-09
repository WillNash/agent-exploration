from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import create_token, require_user
from app.database import get_pool
from app.models import public_customer
from app.services import (
    authenticate_customer,
    create_customer_with_password,
    create_developer_token,
    get_customer_by_email,
    list_developer_tokens,
    revoke_developer_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class CreateTokenIn(BaseModel):
    name: str


@router.post("/register", status_code=201)
async def register(
    body: RegisterIn,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    existing = await get_customer_by_email(pool, body.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="email_already_registered")
    customer = await create_customer_with_password(
        pool, name=body.name, email=body.email, password=body.password
    )
    token = create_token(customer["id"], customer["email"])
    return {"access_token": token, "token_type": "bearer", "customer": public_customer(customer)}


@router.post("/login")
async def login(
    body: LoginIn,
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    customer = await authenticate_customer(pool, email=body.email, password=body.password)
    if customer is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    token = create_token(customer["id"], customer["email"])
    return {"access_token": token, "token_type": "bearer", "customer": public_customer(customer)}


@router.post("/tokens", status_code=201)
async def create_token_endpoint(
    body: CreateTokenIn,
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return await create_developer_token(
        pool, customer_id=int(user["sub"]), name=body.name, email=user["email"]
    )


@router.get("/tokens")
async def list_tokens(
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(require_user),
) -> list[dict[str, Any]]:
    return await list_developer_tokens(pool, int(user["sub"]))


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_token(
    token_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
    user: dict[str, Any] = Depends(require_user),
) -> None:
    revoked = await revoke_developer_token(pool, token_id, int(user["sub"]))
    if not revoked:
        raise HTTPException(status_code=404, detail="token_not_found")
