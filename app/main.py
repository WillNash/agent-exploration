from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore

from app.agent.card import garden_card
from app.agent.executor import GardenStoreExecutor
from app.auth import current_user, decode_token
from app.database import create_pool
from app.routers import auth, customers, health, products, purchases

load_dotenv()


class AuthMiddleware:
    """Pure ASGI middleware — sets the current_user context var before the handler runs.

    Using pure ASGI (not BaseHTTPMiddleware) ensures the context var propagates
    correctly through all async code in the same request, including the A2A executor.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k: v for k, v in scope.get("headers", [])}
            auth_header = headers.get(b"authorization", b"").decode()
            user = None
            if auth_header.startswith("Bearer "):
                user = decode_token(auth_header[7:])
            token = current_user.set(user)
            try:
                await self.app(scope, receive, send)
            finally:
                current_user.reset(token)
        else:
            await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    pool = await create_pool(os.environ["DATABASE_URL"])
    app.state.pool = pool

    executor = GardenStoreExecutor(pool=pool)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=garden_card,
        extended_agent_card=garden_card,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(garden_card),
        jsonrpc_routes=create_jsonrpc_routes(handler, "/rpc"),
        rest_routes=create_rest_routes(handler),
    )

    yield

    await handler.aclose()
    await pool.close()


app = FastAPI(title="Green Thumb Garden Store", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        "http://localhost:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(purchases.router)

_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
