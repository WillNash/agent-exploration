from __future__ import annotations

import os
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# Set by AuthMiddleware for every authenticated request.
# Readable anywhere in the same async call chain — REST handlers, A2A executor, services.
current_user: ContextVar[dict[str, Any] | None] = ContextVar("current_user", default=None)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


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
