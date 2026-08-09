# Green Thumb Garden Store — A2A Protocol Demo

A full-stack demo application that explores the [Agent-to-Agent (A2A) protocol](https://google.github.io/A2A/). It builds a realistic garden store with a PostgreSQL database, a Vue.js web UI, and a Python backend that serves both a conventional REST API and an A2A-compatible JSON-RPC endpoint from the same port. A local LLM agent (via Ollama) can discover the store's capabilities at runtime and act on a user's behalf.

---

## What this demonstrates

- How a backend can advertise its capabilities via an **agent card** at `/.well-known/agent-card.json`
- How an LLM agent reads that card and constructs valid intents **without hardcoded knowledge** of the store
- The difference between REST (human-oriented) and A2A RPC (agent-oriented) on the same backend
- JWT-based authentication shared between the browser UI and the agent
- **Developer tokens** — how a user can hand a scoped credential to an agent without sharing their password

---

## Project structure

```
.
├── app/                        # Python backend (FastAPI + asyncpg)
│   ├── agent/
│   │   ├── card.py             # Agent card definition — the store's public capability advertisement
│   │   ├── executor.py         # Handles incoming A2A intents, calls services, returns results
│   │   └── intents.py          # Typed dataclasses for each supported action
│   ├── routers/
│   │   ├── auth.py             # POST /auth/register, /auth/login, /auth/tokens (CRUD)
│   │   ├── customers.py        # GET /api/customers, /api/customers/me
│   │   ├── health.py           # GET /health
│   │   ├── products.py         # GET /api/products
│   │   └── purchases.py        # GET/POST /api/purchases
│   ├── auth.py                 # JWT creation/validation, bcrypt, current_user ContextVar
│   ├── database.py             # asyncpg connection pool
│   ├── main.py                 # FastAPI app, pure-ASGI auth middleware, A2A route wiring
│   ├── models.py               # TypedDicts and row serialisation helpers
│   └── services.py             # All business logic (shared by REST and A2A)
├── agent_client/
│   ├── agent.py                # CLI agent — discovers card, prompts Ollama, calls /rpc
│   └── agent.ipynb             # Jupyter notebook version with chat widget
├── db/
│   └── init.sql                # Schema creation and seed data
├── frontend/                   # Vue.js 3 single-page application
│   └── src/
│       ├── api/client.js       # All HTTP calls including A2A RPC
│       ├── components/         # AuthModal
│       ├── router/index.js
│       ├── stores/             # cart.js, user.js (localStorage-persisted)
│       └── views/              # ProductList, CartView, CheckoutView, AgentDemo, AccountView
├── backend.Dockerfile
├── frontend.Dockerfile
└── docker-compose.yml
```

---

## How A2A works in this project

### The agent card

Every A2A-compatible service publishes a machine-readable description of itself at:

```
GET /.well-known/agent-card.json
```

This card describes the service name, what it does, and its **skills** — each skill documents an action the agent can take, its intent schema, example intents, and authentication requirements. The card is defined in `app/agent/card.py`.

An agent discovering this store for the first time reads the card and builds its understanding of the store entirely from that document. No store-specific knowledge is baked into the agent code.

### The RPC endpoint

All A2A communication goes through a single endpoint:

```
POST /rpc
```

Requests follow the **JSON-RPC 2.0** envelope format:

```json
{
  "jsonrpc": "2.0",
  "id": "any-unique-id",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [{ "text": "{\"action\": \"browse_products\", \"category\": \"seeds\"}" }],
      "messageId": "msg-1"
    }
  }
}
```

The intent — what you actually want the store to do — is a JSON object serialised as a string inside `parts[0].text`. The A2A envelope is the transport; the intent is the payload.

The response mirrors this structure:

```json
{
  "jsonrpc": "2.0",
  "id": "any-unique-id",
  "result": {
    "message": {
      "role": "ROLE_AGENT",
      "parts": [{ "text": "[{\"id\": 4, \"name\": \"Basil Seeds\", ...}]" }]
    }
  }
}
```

The store's JSON response is again a string in `result.message.parts[0].text`. Parse it to get the structured data.

### The executor

`app/agent/executor.py` receives the decoded intent, dispatches to the appropriate service function in `app/services.py`, and returns a JSON result. It reads the authenticated user from a `ContextVar` set by the auth middleware — the same identity mechanism used by the REST routers.

### Supported actions

| Action | Auth required | Parameters |
|---|---|---|
| `list_categories` | No | none |
| `browse_products` | No | `category` (optional), `max_price` (optional) |
| `get_product` | No | `product_id` (required) |
| `checkout` | Yes | `items: [{product_id, quantity}]` |
| `list_purchases` | Yes | none |

### REST vs A2A side by side

The same business logic serves both interfaces. The REST routers (`/api/products`, `/api/purchases`, etc.) are for the browser UI. The A2A RPC endpoint (`/rpc`) is for agents. Both call the same service functions in `services.py`.

```
Browser  →  GET /api/products?category=seeds  →  products router  →  services.browse_products()
Agent    →  POST /rpc  {"action":"browse_products","category":"seeds"}  →  executor  →  services.browse_products()
```

---

## How the agent works

The agent (`agent_client/agent.py` and `agent.ipynb`) is a simple loop:

1. **Discover** — fetch `/.well-known/agent-card.json` and build a system prompt from the card's skill descriptions
2. **Prompt** — send the user's message to a local Ollama LLM with a single generic tool: `call_agent`
3. **Act** — if the model emits a tool call, extract the intent, POST it to `/rpc`, feed the result back into the conversation
4. **Repeat** — loop until the model produces a plain-text response with no tool calls

The agent has no hardcoded knowledge of the store's products or actions. The LLM learns what it can do entirely from the system prompt derived from the agent card.

```
User message
     │
     ▼
LLM (Ollama) ──── tool call? ────► POST /rpc with intent
     ▲                                      │
     └──────── tool result ─────────────────┘
     │
     ▼ (no tool call)
Agent response to user
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose)
- [Ollama](https://ollama.com/) — for running the local LLM agent
- Python 3.11+ with a virtual environment or conda — for the agent client only

---

## Getting the store running

```bash
# Clone the repo and start everything
git clone <repo-url>
cd agent-exploration

docker compose up --build
```

This starts three containers:

| Container | Port | What it is |
|---|---|---|
| `db` | 5432 | PostgreSQL 16 — schema created from `db/init.sql` on first run |
| `backend` | 8000 | FastAPI — REST API + A2A RPC + agent card |
| `frontend` | 5173 | Vite dev server — Vue.js UI proxied to the backend |

Open http://localhost:5173 to use the store.

> **Rebuilding the database**: if you change `db/init.sql` (schema or seed data), you must drop the volume for the changes to take effect:
> ```bash
> docker compose down -v && docker compose up --build
> ```

---

## Creating an account

The two seeded customers (`alice@example.com`, `bob@example.com`) have no passwords and cannot log in. Create your own account:

1. Click **Create account** in the top-right of the web UI
2. Fill in name, email, and password
3. You are now signed in — browse products, add to cart, and check out

Alternatively, via curl:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Your Name","email":"you@example.com","password":"yourpassword"}'
```

---

## Setting up Ollama

Ollama runs LLMs locally. Install it from https://ollama.com/download, then pull a model:

```bash
# Recommended — reliable tool use, English-only
ollama pull llama3.1:70b

# Smaller alternative if you have limited RAM
ollama pull llama3.1:8b
```

Approximate requirements:

| Model | Disk | RAM |
|---|---|---|
| llama3.1:8b | 4.7 GB | 8 GB |
| llama3.1:70b | 40 GB | 48 GB |

By default Ollama binds to `127.0.0.1:11434` — it is only accessible from your local machine.

> **WSL users**: Ollama running on Windows is not automatically reachable at `localhost` from inside WSL. Find your Windows host IP (`ipconfig` in PowerShell, look for WSL adapter) and set `OLLAMA_BASE` to `http://<host-ip>:11434` in `agent_client/agent.ipynb` or pass `--ollama http://<host-ip>:11434` to `agent.py`.

---

## Creating a developer token

Rather than typing your password into the agent, create a scoped token from the web UI:

1. Sign in to the store
2. Click your name in the top-right nav → **Account**
3. Enter a label (e.g. "my laptop") and click **Create token**
4. Copy the token immediately — it is only shown once

The token is a JWT. It is revocable from the Account page at any time without changing your password.

---

## Using the CLI agent

Install dependencies (use a venv or conda environment):

```bash
pip install openai httpx
# or with conda:
conda install openai httpx
```

Run the agent:

```bash
# Using a developer token (recommended)
python agent_client/agent.py --token <paste-token-here>

# Using email/password (prompted at startup)
python agent_client/agent.py

# Specify a different model
python agent_client/agent.py --model llama3.1:8b --token <token>

# All options
python agent_client/agent.py --help
```

Example session:

```
Connected to Garden Store Agent at http://localhost:8000 — authenticated
Model: llama3.1:70b  |  Type your request, or Ctrl+C to quit.

You: what seeds do you have suitable for sowing in autumn?
  → {"action": "browse_products", "category": "seeds"}
  ← [{"id": 8, "name": "Broad Bean Seeds (Aquadulce)", ...}, ...]

Agent: Here are the seeds suitable for autumn sowing...
```

---

## Using the Jupyter notebook

Install dependencies:

```bash
pip install openai httpx ipywidgets
# or with conda:
conda install openai httpx ipywidgets
```

Open `agent_client/agent.ipynb` in JupyterLab or VS Code. Run the cells in order:

1. **Cell 1** (config) — set `OLLAMA_BASE`, `OLLAMA_MODEL`, and `GARDEN_STORE` if needed
2. **Cell 2** (helpers) — defines the A2A helper functions and tool spec
3. **Login cell** — two options:
   - Paste a developer token from the Account page (recommended)
   - Enter email and password
   - Press Enter at both prompts to browse without logging in
4. **Init cell** — connects to the store and builds the system prompt from the agent card
5. **Chat cell** — displays the interactive chat widget

The chat widget grows as the conversation continues. Use **Clear chat** to reset the conversation history (useful if the model starts misbehaving or responding in a wrong language — clearing removes the bad history from context).

---

## Accessing the database

Connect to PostgreSQL directly via Docker:

```bash
docker compose exec db psql -U garden -d garden_store
```

Useful queries:

```sql
-- See all tables
\dt

-- Browse products
SELECT id, name, price, category, stock_qty FROM products ORDER BY category, name;

-- See registered customers (passwords are bcrypt-hashed)
SELECT id, name, email, created_at FROM customers;

-- See all purchases
SELECT cp.id, c.name, p.name AS product, cp.quantity, cp.purchased_at
FROM customer_purchases cp
JOIN customers c ON c.id = cp.customer_id
JOIN products p ON p.id = cp.product_id
ORDER BY cp.purchased_at DESC;

-- See developer tokens
SELECT id, customer_id, name, created_at, revoked_at FROM developer_tokens;

-- Quit
\q
```

---

## Authentication architecture

The store uses **JWT Bearer tokens** for all protected actions, shared between the web UI and the A2A interface.

```
Browser login  →  POST /auth/login  →  JWT (24h expiry)  →  stored in localStorage
Agent login    →  POST /auth/login  →  JWT (24h expiry)  →  passed as --token arg

Developer token  →  POST /auth/tokens  →  long-lived JWT  →  stored in developer_tokens table
                                                              revocable via DELETE /auth/tokens/{id}
```

The `Authorization: Bearer <token>` header is accepted on all endpoints — both REST (`/api/...`) and A2A (`/rpc`). A pure-ASGI middleware validates the token before the request reaches any handler and stores the decoded identity in a Python `ContextVar`, making it available to both FastAPI route handlers and the A2A executor without any duplication.

Developer tokens are validated against the database on every request to support revocation. Regular login tokens are stateless (no DB lookup needed — expiry is checked from the JWT itself).
