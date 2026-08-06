#!/usr/bin/env python3
"""
Local agent for the Garden Store using Ollama + A2A.

Requirements:
    pip install openai httpx

Usage:
    python agent_client/agent.py
    python agent_client/agent.py --model llama3.1:8b
    python agent_client/agent.py --store http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Tools — one per A2A intent action
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "List all product categories available in the store.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_products",
            "description": "Browse products, optionally filtered by category or max price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category name to filter by"},
                    "max_price": {"type": "number", "description": "Maximum price in GBP"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get full details for a single product by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_customer",
            "description": (
                "Register a new customer or update an existing customer's name by email. "
                "Always call this before checkout if the customer may not exist yet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": "Place an order for a customer. Customer must exist first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "integer"},
                                "quantity": {"type": "integer"},
                            },
                            "required": ["product_id", "quantity"],
                        },
                    },
                },
                "required": ["customer_email", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_purchases",
            "description": "List purchase history for a customer by email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {"type": "string"},
                },
                "required": ["customer_email"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# A2A client
# ---------------------------------------------------------------------------

_rpc_seq = 0


def a2a_call(store_base: str, intent: dict) -> dict:
    global _rpc_seq
    _rpc_seq += 1
    payload = {
        "jsonrpc": "2.0",
        "id": f"agent-{_rpc_seq}",
        "method": "SendMessage",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": json.dumps(intent)}],
                "messageId": f"msg-{_rpc_seq}",
            }
        },
    }
    r = httpx.post(
        f"{store_base}/rpc",
        json=payload,
        headers={"Content-Type": "application/json", "A2A-Version": "1.0"},
        timeout=30,
    )
    r.raise_for_status()
    envelope = r.json()
    if "error" in envelope:
        return {"error": envelope["error"]}
    text = envelope["result"]["message"]["parts"][0]["text"]
    return json.loads(text)


def fetch_card(store_base: str) -> dict:
    r = httpx.get(f"{store_base}/.well-known/agent-card.json", timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run(model: str, store_base: str, ollama_base: str) -> None:
    card = fetch_card(store_base)

    llm = OpenAI(base_url=f"{ollama_base}/v1", api_key="ollama")

    system = (
        f"You are a helpful shopping assistant for the {card['name']}. "
        f"{card['description']} "
        "Use the provided tools to fulfil the user's requests. "
        "When browsing, summarise results concisely — don't dump raw JSON at the user. "
        "Always confirm the items and total before calling checkout. "
        "If a checkout requires creating a customer first, do so automatically without asking."
    )

    messages: list[dict] = [{"role": "system", "content": system}]
    print(f"Connected to {card['name']} at {store_base}")
    print(f"Model: {model}  |  Type your request, or Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            sys.exit(0)

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Inner loop: keep processing tool calls until the model gives a plain reply.
        while True:
            response = llm.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                print(f"\nAgent: {msg.content}\n")
                break

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                print(f"  → {tc.function.name}({json.dumps(args)})")
                result = a2a_call(store_base, {"action": tc.function.name, **args})
                print(f"  ← {json.dumps(result)[:120]}{'…' if len(json.dumps(result)) > 120 else ''}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Garden Store local agent")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--store", default="http://localhost:8000", help="Garden store base URL")
    parser.add_argument("--ollama", default="http://localhost:11434", help="Ollama base URL")
    args = parser.parse_args()
    run(model=args.model, store_base=args.store, ollama_base=args.ollama)


if __name__ == "__main__":
    main()
