from __future__ import annotations

from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import create_token
from app.database import get_pool
from app.models import public_customer
from app.services import authenticate_customer, create_customer_with_password, get_customer_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


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
