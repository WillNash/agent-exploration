#!/usr/bin/env python3
"""
Local agent for any A2A-compatible service, using Ollama.

Capabilities are discovered at runtime from the agent card — this script
has no hardcoded knowledge of the store's actions or structure.

Requirements:
    pip install openai httpx

Usage:
    python agent_client/agent.py
    python agent_client/agent.py --model llama3.1:8b
    python agent_client/agent.py --store http://localhost:8000
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys

import httpx
from openai import OpenAI

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "call_agent",
            "description": (
                "Send a JSON intent to the agent and receive a response. "
                "Construct the intent object exactly as documented in the available actions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "object",
                        "description": (
                            'A JSON object with an "action" field and the parameters '
                            "for that action, as documented in the system prompt."
                        ),
                    }
                },
                "required": ["intent"],
            },
        },
    }
]


def fetch_card(store_base: str) -> dict:
    r = httpx.get(f"{store_base}/.well-known/agent-card.json", timeout=10)
    r.raise_for_status()
    return r.json()


def authenticate(store_base: str) -> str | None:
    """Prompt for credentials and return a Bearer token, or None to skip."""
    print("\nThis store requires authentication for checkout and purchase history.")
    print("Press Enter to skip (browsing still works without login).\n")
    email = input("Email (or Enter to skip): ").strip()
    if not email:
        return None
    password = getpass.getpass("Password: ")
    r = httpx.post(
        f"{store_base}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code == 401:
        print("Invalid credentials — continuing without authentication.")
        return None
    r.raise_for_status()
    token = r.json()["access_token"]
    name = r.json()["customer"]["name"]
    print(f"Signed in as {name}.\n")
    return token


def build_system_prompt(card: dict) -> str:
    skills = card.get("skills", [])
    skills_text = "\n\n".join(
        "Action: {name}\n{description}\nExample intent: {example}".format(
            name=s["name"],
            description=s["description"],
            example=s.get("examples", ["(none)"])[0],
        )
        for s in skills
    )
    return (
        f"You are a helpful assistant for {card['name']}.\n\n"
        f"{card['description']}\n\n"
        f"## Available actions\n\n{skills_text}\n\n"
        "## Rules you must follow\n\n"
        "0. ALWAYS respond in English, regardless of any other language you detect.\n"
        "1. If you need data from the store, call the tool NOW — do not say you will call it, "
        "do not explain what you are about to do, just call it immediately.\n"
        "2. NEVER invent or guess a product_id. "
        "Always call browse_products first to find the correct product_id before checkout.\n"
        "3. NEVER describe placing an order or confirm a result unless a tool call was actually made.\n"
        "4. Once the user confirms checkout, call the tool immediately — do not narrate, just act.\n"
        "5. Summarise tool results in plain English. Do not show raw JSON to the user.\n"
        "6. If a tool returns {\"error\": \"unauthorized\"}, tell the user they need to log in.\n"
        "7. You may combine tool results with your own general knowledge. For example: call "
        "browse_products to see what is available, then use your own knowledge to answer "
        "questions like which products suit a season, a climate, or a skill level."
    )


_rpc_seq = 0


def a2a_call(store_base: str, intent: dict, token: str | None) -> dict:
    global _rpc_seq
    _rpc_seq += 1
    headers = {"Content-Type": "application/json", "A2A-Version": "1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
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
    r = httpx.post(f"{store_base}/rpc", json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    envelope = r.json()
    if "error" in envelope:
        return {"error": envelope["error"]}
    text = envelope["result"]["message"]["parts"][0]["text"]
    return json.loads(text)


def run(model: str, store_base: str, ollama_base: str, token: str | None = None) -> None:
    card = fetch_card(store_base)
    if token is None:
        token = authenticate(store_base)
    else:
        print("Using developer token.\n")
    system = build_system_prompt(card)
    llm = OpenAI(base_url=f"{ollama_base}/v1", api_key="ollama")

    messages: list[dict] = [{"role": "system", "content": system}]
    auth_status = "authenticated" if token else "browsing only (not authenticated)"
    print(f"Connected to {card['name']} at {store_base} — {auth_status}")
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
                intent = args.get("intent", args)
                print(f"  → {json.dumps(intent)}")
                result = a2a_call(store_base, intent, token)
                summary = json.dumps(result)
                print(f"  ← {summary[:120]}{'…' if len(summary) > 120 else ''}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic A2A agent powered by Ollama")
    parser.add_argument("--model", default="llama3.1:8b", help="Ollama model name")
    parser.add_argument("--store", default="http://localhost:8000", help="A2A service base URL")
    parser.add_argument("--ollama", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--token", default=None, help="Developer token (skips login prompt)")
    args = parser.parse_args()
    run(model=args.model, store_base=args.store, ollama_base=args.ollama, token=args.token)


if __name__ == "__main__":
    main()
