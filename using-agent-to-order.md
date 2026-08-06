# Using a Local Agent to Place Orders

This guide walks through setting up a local AI agent that can browse the garden store and place orders on your behalf, using the A2A interface.

The agent discovers everything it needs from the agent card at `/.well-known/agent-card.json` — it has no hardcoded knowledge of the store's actions, parameters, or structure. The same script works against any A2A-compatible service; point it at a different `--store` URL and it discovers that service's capabilities automatically.

## How it works

The garden store exposes an A2A interface at `/rpc`. The agent:

1. Fetches the agent card to understand what actions are available
2. Takes your request in plain English
3. Decides which store actions to call and in what order
4. Calls the store via JSON-RPC and interprets the results
5. Responds to you in plain English

The tool calls are printed as they happen so you can follow the agent's reasoning.

## Prerequisites

- The garden store running locally (`docker compose up`)
- Python 3.11+ on your host or in WSL
- [Ollama](https://ollama.com) installed (see below)

## Step 1 — Install Ollama

Download the installer from **ollama.com**. If you are on Windows with WSL, install Ollama on Windows (not inside WSL) so it can use your GPU if you have one. WSL can reach it over `localhost` without any extra configuration.

## Step 2 — Pull a model

Open a terminal and run:

```
ollama pull qwen2.5:7b
```

### Model options

| Model | Download size | Notes |
|---|---|---|
| `qwen2.5:7b` | ~5 GB | Best tool-calling at this size — recommended |
| `llama3.1:8b` | ~5 GB | Meta, strong all-rounder |
| `qwen2.5:3b` | ~2 GB | Use if RAM is tight; quality drops noticeably |

**qwen2.5:7b** is recommended because small models vary significantly in their ability to call tools reliably, and Qwen 2.5 consistently performs well at this task.

## Step 3 — Install Python dependencies

Run this on your host or in WSL, outside of Docker:

```
pip install openai httpx
```

The script uses the `openai` library pointed at Ollama's OpenAI-compatible endpoint — no OpenAI account or API key is needed.

## Step 4 — Run the agent

From the repo root:

```
python agent_client/agent.py
```

Options:

```
python agent_client/agent.py --model llama3.1:8b
python agent_client/agent.py --store http://localhost:8000
python agent_client/agent.py --ollama http://localhost:11434
```

## Example session

```
Connected to Garden Store Agent at http://localhost:8000
Model: qwen2.5:7b  |  Type your request, or Ctrl+C to quit.

You: I need some seeds under £5, order 2 packets for alice@example.com

  → browse_products({"category": "seeds", "max_price": 5.0})
  ← [{"id": 1, "name": "Sunflower Seeds", "price": 3.99, ...}, ...]
  → create_customer({"name": "Alice", "email": "alice@example.com"})
  ← {"id": 1, "name": "Alice", "email": "alice@example.com", ...}
  → checkout({"customer_email": "alice@example.com", "items": [{"product_id": 1, "quantity": 2}]})
  ← {"status": "confirmed", "order_total": 7.98, ...}

Agent: Done! I've placed an order for 2 packets of Sunflower Seeds (£3.99 each)
       for alice@example.com. Order total: £7.98.

You: What has alice ordered before?

  → list_purchases({"customer_email": "alice@example.com"})
  ← [{"product_name": "Sunflower Seeds", "quantity": 2, "purchased_at": "..."}]

Agent: Alice has one previous order: 2 packets of Sunflower Seeds, purchased today.
```

## How the agent card enables this

The agent fetches `/.well-known/agent-card.json` on startup and builds the entire system prompt from it — the service name, description, and every skill with its parameter schema and example intent. The code exposes a single generic transport tool (`call_agent`) that sends whatever intent JSON the LLM constructs.

The LLM reads the card and figures out what to call and how to call it. The script itself has no knowledge of `browse_products`, `checkout`, or any other action — those exist only in the card.

## A note on trust

There is no password on the A2A interface. Anyone who knows a customer's email can place orders as that customer. This is intentional for this demo — the trust model is "if you know the email, you are that customer." A production system would add token-based authentication to the `/rpc` endpoint.
