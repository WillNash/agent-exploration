from __future__ import annotations

import json
import logging
import os
from typing import Any

_MAX_ITERATIONS = 10

import asyncpg
from openai import AsyncOpenAI

from a2a.helpers.proto_helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from app.auth import current_user
from app.services import (
    CheckoutItem,
    InsufficientStockError,
    ProductNotFoundError,
    browse_products,
    checkout,
    get_product,
    list_categories,
    list_purchases,
)

logger = logging.getLogger(__name__)

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:70b")

# ---------------------------------------------------------------------------
# Tool schemas passed to the LLM
# ---------------------------------------------------------------------------

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "Return all distinct product categories available in the garden store. No parameters required.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_products",
            "description": (
                "List garden products, optionally filtered by category or maximum price. "
                "Returns an array of product objects with fields: id, name, description, price, category, stock_qty."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter to products in this category (case-sensitive). Optional.",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Only return products at or below this price. Optional.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": (
                "Retrieve full details for a single product by its integer ID. "
                "Returns a product object, or an error if the ID does not exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "The integer ID of the product to retrieve.",
                    }
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": (
                "Place an order for one or more products on behalf of the authenticated customer. "
                "Requires the user to be authenticated (Bearer token). "
                "Customer identity is taken from the auth context — do not ask for or include customer details. "
                "Returns a confirmation with order total, or an error for insufficient stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of items to purchase.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {
                                    "type": "integer",
                                    "description": "The integer ID of the product.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Number of units to purchase.",
                                },
                            },
                            "required": ["product_id", "quantity"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_purchases",
            "description": (
                "Return the full purchase history for the authenticated customer, most recent first. "
                "Requires the user to be authenticated (Bearer token). No parameters needed."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

_SYSTEM_PROMPT = """\
You are a helpful assistant for the Green Thumb garden store.
You have access to tools that let you browse products, look up product details, \
place orders, and view purchase history.

Rules:
1. Always respond in plain English — never show raw JSON to the user.
2. If you need information from the store, call the appropriate tool immediately \
   without narrating that you are about to do so.
3. Never invent or guess a product_id. Call browse_products first to find the \
   correct product_id before calling checkout.
4. Never confirm an order unless a checkout tool call actually succeeded.
5. If a tool returns an error indicating the user is not authenticated, tell them \
   they need to provide a valid Bearer token.
6. Summarise tool results concisely in natural language.
"""


class GardenStoreExecutor(AgentExecutor):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._llm = AsyncOpenAI(
            base_url=f"{_OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = context.get_user_input()
        try:
            response_text = await self._run_agent(user_text)
        except Exception as exc:
            logger.exception("Agent loop failed: %s", exc)
            response_text = "I'm sorry, I encountered an error processing your request. Please try again."
        await event_queue.enqueue_event(new_text_message(response_text))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancellation is not supported")

    # ------------------------------------------------------------------
    # Agent loop
    # ------------------------------------------------------------------

    async def _run_agent(self, user_text: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

        for _ in range(_MAX_ITERATIONS):
            response = await self._llm.chat.completions.create(
                model=_OLLAMA_MODEL,
                messages=messages,
                tools=_TOOLS,
            )
            msg = response.choices[0].message

            # Convert the message to a plain dict for appending to history
            messages.append(msg.model_dump(exclude_unset=True))

            if not msg.tool_calls:
                # LLM produced a final text reply
                return msg.content or ""

            # Execute each tool call and feed results back
            for tc in msg.tool_calls:
                result = await self._dispatch_tool(tc.function.name, tc.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        raise RuntimeError(f"Agent exceeded {_MAX_ITERATIONS} iterations without producing a final answer")

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _dispatch_tool(self, name: str, arguments_json: str) -> Any:
        try:
            args: dict[str, Any] = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            return {"error": "invalid_tool_arguments", "tool": name}

        logger.debug("tool call: %s(%s)", name, args)

        match name:
            case "list_categories":
                return await list_categories(self._pool)

            case "browse_products":
                return await browse_products(
                    self._pool,
                    category=args.get("category"),
                    max_price=float(args["max_price"]) if args.get("max_price") is not None else None,
                )

            case "get_product":
                if "product_id" not in args:
                    return {"error": "missing_argument", "argument": "product_id"}
                product = await get_product(self._pool, int(args["product_id"]))
                if product is None:
                    return {"error": "product_not_found", "product_id": args["product_id"]}
                return product

            case "checkout":
                return await self._checkout(args)

            case "list_purchases":
                return await self._list_purchases()

            case _:
                return {"error": "unknown_tool", "tool": name}

    async def _checkout(self, args: dict[str, Any]) -> dict[str, Any]:
        user = current_user.get()
        if user is None:
            return {
                "error": "unauthorized",
                "hint": "A valid Bearer token is required to place an order.",
            }
        try:
            customer_id = int(user["sub"])
        except (ValueError, KeyError):
            return {"error": "invalid_token", "hint": "The Bearer token does not contain a valid user identity."}
        try:
            raw_items = args.get("items", [])
            if not raw_items:
                return {"error": "checkout_requires_items", "hint": "Provide at least one item to purchase."}
            for i in raw_items:
                if not isinstance(i, dict):
                    return {"error": "invalid_item", "hint": "Each item must be an object with product_id and quantity."}
                if "product_id" not in i:
                    return {"error": "missing_argument", "argument": "product_id", "hint": "Each item must include a product_id."}
                if isinstance(i["product_id"], (float, bool)):
                    return {"error": "invalid_argument", "argument": "product_id", "hint": "product_id must be an integer."}
                try:
                    int(i["product_id"])
                except (ValueError, TypeError):
                    return {"error": "invalid_argument", "argument": "product_id", "hint": "product_id must be an integer."}
                if "quantity" not in i:
                    return {"error": "missing_argument", "argument": "quantity", "hint": "Each item must include a quantity."}
                try:
                    qty = int(i["quantity"])
                except (ValueError, TypeError):
                    return {"error": "invalid_quantity", "hint": "Each item's quantity must be an integer."}
                if qty < 1:
                    return {"error": "invalid_quantity", "hint": "Each item must have a quantity of at least 1."}
            return await checkout(
                self._pool,
                customer_id=customer_id,
                items=[
                    CheckoutItem(
                        product_id=int(i["product_id"]),
                        quantity=int(i["quantity"]),
                    )
                    for i in raw_items
                ],
            )
        except ProductNotFoundError as e:
            return {"error": "product_not_found", "product_id": e.product_id}
        except InsufficientStockError as e:
            return {
                "error": "insufficient_stock",
                "product": e.product_name,
                "requested": e.requested,
                "available": e.available,
            }

    async def _list_purchases(self) -> list[dict[str, Any]] | dict[str, Any]:
        user = current_user.get()
        if user is None:
            return {
                "error": "unauthorized",
                "hint": "A valid Bearer token is required to view purchase history.",
            }
        try:
            customer_id = int(user["sub"])
        except (ValueError, KeyError):
            return {"error": "invalid_token", "hint": "The Bearer token does not contain a valid user identity."}
        return await list_purchases(self._pool, customer_id)
