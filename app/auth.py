from __future__ import annotations

import os
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Set by AuthMiddleware for every authenticated request.
# Readable anywhere in the same async call chain — REST handlers, A2A executor, services.
current_user: ContextVar[dict[str, Any] | None] = ContextVar("current_user", default=None)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(customer_id: int, email: str) -> str:
    payload = {
        "sub": str(customer_id),
        "email": email,
        "exp": datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
