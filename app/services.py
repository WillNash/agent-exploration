from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg

from app.models import row_to_dict


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class CustomerNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"customer not found: {identifier}")


class ProductNotFoundError(Exception):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"product not found: {product_id}")


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, requested: int, available: int) -> None:
        self.product_name = product_name
        self.requested = requested
        self.available = available
        super().__init__(
            f"insufficient stock for '{product_name}': "
            f"requested {requested}, available {available}"
        )


# ---------------------------------------------------------------------------
# Auth services
# ---------------------------------------------------------------------------

async def create_customer_with_password(
    pool: asyncpg.Pool, *, name: str, email: str, password: str
) -> dict[str, Any]:
    from app.auth import hash_password
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO customers (name, email, password_hash)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            name,
            email,
            hash_password(password),
        )
    return row_to_dict(row)


async def authenticate_customer(
    pool: asyncpg.Pool, *, email: str, password: str
) -> dict[str, Any] | None:
    from app.auth import verify_password
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM customers WHERE email = $1", email)
    if row is None or not row["password_hash"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return row_to_dict(row)


# ---------------------------------------------------------------------------
# Product services
# ---------------------------------------------------------------------------

async def list_categories(pool: asyncpg.Pool) -> list[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT category FROM products "
            "WHERE category IS NOT NULL ORDER BY category"
        )
    return [r["category"] for r in rows]


async def browse_products(
    pool: asyncpg.Pool,
    *,
    category: str | None = None,
    max_price: float | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM products WHERE 1=1"
    args: list[Any] = []

    if category is not None:
        args.append(category)
        query += f" AND category = ${len(args)}"

    if max_price is not None:
        args.append(max_price)
        query += f" AND price <= ${len(args)}"

    query += " ORDER BY category, name"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)

    return [row_to_dict(r) for r in rows]


async def get_product(pool: asyncpg.Pool, product_id: int) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    return row_to_dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Customer services
# ---------------------------------------------------------------------------

async def upsert_customer(
    pool: asyncpg.Pool, *, name: str, email: str
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
            name,
            email,
        )
    return row_to_dict(row)


async def get_customer_by_email(
    pool: asyncpg.Pool, email: str
) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM customers WHERE email = $1", email)
    return row_to_dict(row) if row is not None else None


async def get_customer_by_id(
    pool: asyncpg.Pool, customer_id: int
) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
    return row_to_dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Purchase services
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class CheckoutItem:
    product_id: int
    quantity: int


async def checkout(
    pool: asyncpg.Pool,
    *,
    customer_id: int,
    items: list[CheckoutItem],
) -> dict[str, Any]:
    """
    Raises ProductNotFoundError or InsufficientStockError on failure.
    The customer_id must come from the authenticated session — no lookup performed.
    """
    async with pool.acquire() as conn:
        order_rows: list[dict[str, Any]] = []

        async with conn.transaction():
            for item in items:
                product = await conn.fetchrow(
                    "SELECT id, name, price, stock_qty FROM products "
                    "WHERE id = $1 FOR UPDATE",
                    item.product_id,
                )
                if product is None:
                    raise ProductNotFoundError(item.product_id)
                if product["stock_qty"] < item.quantity:
                    raise InsufficientStockError(
                        product["name"], item.quantity, product["stock_qty"]
                    )

                await conn.execute(
                    "UPDATE products SET stock_qty = stock_qty - $1 WHERE id = $2",
                    item.quantity,
                    item.product_id,
                )
                purchase_row = await conn.fetchrow(
                    """
                    INSERT INTO customer_purchases (customer_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    customer_id,
                    item.product_id,
                    item.quantity,
                )
                order_rows.append(
                    {
                        "purchase_id": purchase_row["id"],
                        "product_id": item.product_id,
                        "product_name": product["name"],
                        "quantity": item.quantity,
                        "unit_price": float(product["price"]),
                        "line_total": float(product["price"]) * item.quantity,
                    }
                )

    total = sum(r["line_total"] for r in order_rows)
    return {
        "status": "confirmed",
        "customer_id": customer_id,
        "items": order_rows,
        "order_total": round(total, 2),
    }


async def list_purchases(
    pool: asyncpg.Pool, customer_id: int
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                cp.id,
                cp.customer_id,
                cp.product_id,
                p.name  AS product_name,
                p.price AS price,
                cp.quantity,
                cp.purchased_at
            FROM customer_purchases cp
            JOIN products p ON p.id = cp.product_id
            WHERE cp.customer_id = $1
            ORDER BY cp.purchased_at DESC
            """,
            customer_id,
        )
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Developer token services
# ---------------------------------------------------------------------------

async def create_developer_token(
    pool: asyncpg.Pool, *, customer_id: int, name: str, email: str
) -> dict[str, Any]:
    from app.auth import create_developer_token_jwt
    jti = str(uuid.uuid4())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO developer_tokens (customer_id, name, jti) VALUES ($1, $2, $3) RETURNING *",
            customer_id,
            name,
            jti,
        )
    result = row_to_dict(row)
    result["token"] = create_developer_token_jwt(customer_id, email, jti)
    return result


async def list_developer_tokens(
    pool: asyncpg.Pool, customer_id: int
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, customer_id, name, created_at, revoked_at "
            "FROM developer_tokens WHERE customer_id = $1 ORDER BY created_at DESC",
            customer_id,
        )
    return [row_to_dict(r) for r in rows]


async def revoke_developer_token(
    pool: asyncpg.Pool, token_id: int, customer_id: int
) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE developer_tokens SET revoked_at = NOW() "
            "WHERE id = $1 AND customer_id = $2 AND revoked_at IS NULL",
            token_id,
            customer_id,
        )
    return result == "UPDATE 1"


async def is_token_revoked(pool: asyncpg.Pool, jti: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT revoked_at FROM developer_tokens WHERE jti = $1", jti
        )
    if row is None:
        return True  # Unknown JTI — treat as revoked
    return row["revoked_at"] is not None
