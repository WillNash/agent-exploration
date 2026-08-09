# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Green Thumb Garden Store — a demo app for the [A2A (Agent-to-Agent) protocol](https://google.github.io/A2A/). It shows how a single FastAPI backend can serve both a conventional REST API (for a Vue.js browser UI) and an A2A-compatible JSON-RPC endpoint, with a local LLM agent that discovers the store's capabilities at runtime and acts on a user's behalf via Ollama.

## Running the app

```bash
# Start everything (PostgreSQL + FastAPI backend + Vite frontend)
docker compose up --build

# Rebuild the database (after changing db/init.sql)
docker compose down -v && docker compose up --build
```

Services after startup:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Agent card: http://localhost:8000/.well-known/agent-card.json

## Backend development

The backend uses `uv` for package management. The `pyproject.toml` uses `uv_build` as the build backend. To install dependencies locally:

```bash
uv sync
```

Run the backend directly (requires a running PostgreSQL and a `.env` file based on `.env.example`):

```bash
cp .env.example .env
uvicorn app.main:app --reload
```

## Frontend development

```bash
cd frontend
npm install
npm run dev    # Vite dev server on :5173
npm run build  # Production build to frontend/dist/
```

## Agent client

Install dependencies (use a venv):

```bash
pip install openai httpx
```

Run the CLI agent:

```bash
python agent_client/agent.py --token <developer-token>
python agent_client/agent.py --model llama3.1:8b --token <token>
```

Requires Ollama running locally with a model pulled:

```bash
ollama pull llama3.1:70b   # recommended
ollama pull llama3.1:8b    # smaller alternative
```

## Database access

```bash
docker compose exec db psql -U garden -d garden_store
```

## Architecture

### Dual-interface backend

The same business logic in `app/services.py` serves two interfaces:

```
Browser  →  GET /api/products  →  app/routers/products.py  →  services.browse_products()
Agent    →  POST /rpc          →  app/agent/executor.py    →  services.browse_products()
```

The REST routers (`app/routers/`) are for the browser. The A2A executor (`app/agent/executor.py`) is for LLM agents. Neither contains business logic — they both delegate entirely to `app/services.py`.

### A2A request flow

1. Client POSTs a JSON-RPC 2.0 envelope to `/rpc` with `method="SendMessage"`
2. The intent (a JSON object like `{"action": "browse_products", "category": "seeds"}`) is serialised as a string in `params.message.parts[0].text`
3. `GardenStoreExecutor.execute()` calls `parse_intent()` to decode it into a typed dataclass
4. The executor dispatches to the appropriate service function and returns the result as a JSON string in `result.message.parts[0].text`

The agent card at `/.well-known/agent-card.json` (defined in `app/agent/card.py`) is what an LLM agent fetches first to discover available actions, their schemas, and auth requirements — no store-specific knowledge is baked into the agent client.

### Authentication

A pure-ASGI `AuthMiddleware` in `app/main.py` runs before every handler and stores the decoded JWT payload in a Python `ContextVar` (`current_user` in `app/auth.py`). Both FastAPI route handlers and the A2A executor read identity from this `ContextVar` — there is no separate auth path for REST vs A2A.

Two token types:
- **Login tokens** — stateless JWTs (24h expiry), validated by signature + expiry only
- **Developer tokens** — long-lived JWTs with a `jti` claim, validated against the `developer_tokens` DB table on every request to support revocation

### Key files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app setup, `AuthMiddleware`, A2A route wiring |
| `app/auth.py` | JWT creation/validation, `current_user` ContextVar, `require_user()` dependency |
| `app/services.py` | All business logic — shared by REST and A2A |
| `app/agent/card.py` | The agent card definition (advertised skills, schemas, examples) |
| `app/agent/executor.py` | A2A intent dispatcher — reads `current_user`, calls services |
| `app/agent/intents.py` | Typed dataclasses for each action + `parse_intent()` |
| `app/models.py` | `row_to_dict()` helper for asyncpg rows |
| `app/database.py` | asyncpg connection pool setup |
| `db/init.sql` | Schema and seed data |
| `server.py` | Standalone echo server — minimal A2A reference implementation |
| `agent_client/agent.py` | CLI agent (discover card → prompt Ollama → call `/rpc` loop) |

### A2A SDK usage (v1.1.x)

- Helpers live in `a2a.helpers.proto_helpers` — use `new_text_message()` and `new_text_part()`
- Field names are `snake_case` throughout
- Register routes with `add_a2a_routes_to_fastapi()` (FastAPI) or `create_agent_card_routes()` + `create_jsonrpc_routes()` (bare Starlette)
- `GardenStoreExecutor` uses the simple immediate-response pattern (`enqueue_event(new_text_message(...))`) — no `TaskUpdater` needed since all actions complete synchronously
