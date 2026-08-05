# A2A (Agent-to-Agent) Protocol: How-To Guide

A practical guide to setting up and testing the Agent2Agent protocol — from zero to a working client/server pair.

---

## What is A2A?

A2A is an open protocol (Apache 2.0) that lets AI agents discover and talk to each other, regardless of what framework built them. Think of it as HTTP for agents: a standard transport so a LangGraph agent can call a CrewAI agent without either side needing to know the other's internals.

**Complements MCP** — MCP handles agent-to-tool communication; A2A handles agent-to-agent communication.

**The three pillars:**
- **AgentCard** — a JSON document at `/.well-known/agent-card.json` that advertises what the agent can do
- **Tasks** — stateful units of work with a lifecycle: `submitted → working → completed/failed`
- **Transport** — HTTP + JSON-RPC 2.0, with optional SSE streaming and push notifications

---

## Prerequisites

- Python 3.10+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Two terminal windows (one for server, one for client)

---

## 1. Project Setup

```bash
mkdir a2a-sandbox && cd a2a-sandbox
uv init
uv add "a2a-sdk[http-server]" uvicorn httpx
```

Your directory will look like:

```
a2a-sandbox/
├── .venv/
├── pyproject.toml
├── uv.lock
└── main.py      ← you create this
```

---

## 2. Core Concepts Before You Code

### AgentSkill

A single capability your agent exposes. Clients use this to know what to ask for.

```python
from a2a.types import AgentSkill

skill = AgentSkill(
    id='echo_bot',
    name='Echo Bot',
    description='Echoes back whatever you send.',
    input_modes=['text/plain'],
    output_modes=['text/plain'],
    tags=['echo', 'demo'],
    examples=['hello', 'how are you'],
)
```

### AgentCard

The agent's public identity — served at `/.well-known/agent-card.json`. Clients fetch this first to discover the agent's endpoint, capabilities, and auth requirements.

```python
from a2a.types import AgentCard, AgentCapabilities, AgentInterface

card = AgentCard(
    name='Echo Agent',
    description='A simple demo agent.',
    version='0.0.1',
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC',
            url='http://127.0.0.1:9999',
            protocol_version='1.0',
        )
    ],
    skills=[skill],
)
```

### AgentExecutor

Where your agent's logic lives. The SDK calls `execute()` for each incoming task. Two valid workflows:

**Simple (immediate Message response):**
```python
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.helpers.proto_helpers import new_text_message

class EchoExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        user_text = context.get_user_input()
        await event_queue.enqueue_event(new_text_message(f"Echo: {user_text}"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise NotImplementedError
```

**Task-based (streaming / long-running) using `TaskUpdater`:**
```python
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.helpers.proto_helpers import new_text_part

class EchoExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.start_work()
        user_text = context.get_user_input()
        await updater.add_artifact(
            parts=[new_text_part(f"Echo: {user_text}")],
            last_chunk=True,   # required — signals end of stream
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise NotImplementedError
```

`TaskUpdater` also has `failed()`, `requires_input()`, and `requires_auth()` for other task states.

---

## 3. Build the Server

> **SDK version note:** These examples are correct for `a2a-sdk==1.1.x`. The
> helpers live in `a2a.helpers.proto_helpers`, field names are `snake_case`,
> and `TaskStatusUpdateEvent` wraps state inside a `TaskStatus` object.

Create `server.py`:

```python
import uvicorn
from starlette.applications import Starlette

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.helpers.proto_helpers import new_text_message, new_text_part
from a2a.types import AgentCard, AgentCapabilities, AgentInterface, AgentSkill


# --- Agent logic ---

class EchoExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        user_text = context.get_user_input()

        # Simple workflow: enqueue a single Message and return.
        # For streaming / long-running tasks use TaskUpdater (see below).
        await event_queue.enqueue_event(
            new_text_message(f"Echo: {user_text}")
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise NotImplementedError


# --- Card & server setup ---

skill = AgentSkill(
    id='echo_bot',
    name='Echo Bot',
    description='Echoes back whatever you send.',
    input_modes=['text/plain'],
    output_modes=['text/plain'],
    tags=['echo'],
    examples=['hello'],
)

card = AgentCard(
    name='Echo Agent',
    description='A simple demo agent.',
    version='0.0.1',
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[
        AgentInterface(
            protocol_binding='JSONRPC',
            url='http://127.0.0.1:9999',
            protocol_version='1.0',
        )
    ],
    skills=[skill],
)

handler = DefaultRequestHandler(
    agent_executor=EchoExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=card,
    extended_agent_card=card,
)

routes = []
routes.extend(create_agent_card_routes(card))
routes.extend(create_jsonrpc_routes(handler, '/'))

app = Starlette(routes=routes)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=9999)
```

Run it:

```bash
uv run python server.py
```

You should see `Application startup complete.`

Verify the AgentCard is being served:

```bash
curl http://127.0.0.1:9999/.well-known/agent-card.json | python3 -m json.tool
```

---

## 4. Build the Client

In a second terminal, create `client.py`:

```python
import asyncio
import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest


async def main():
    async with httpx.AsyncClient() as http:
        # Step 1: discover the agent
        resolver = A2ACardResolver(httpx_client=http, base_url='http://127.0.0.1:9999')
        agent_card = await resolver.get_agent_card()
        print(f"Found agent: {agent_card.name}")

        # Step 2: create a client
        client = await create_client(
            agent=agent_card,
            client_config=ClientConfig(streaming=False),
        )

        # Step 3: send a message
        request = SendMessageRequest(
            message=new_text_message("Hello from the client!", role=Role.ROLE_USER)
        )

        async for chunk in client.send_message(request):
            print(chunk)


asyncio.run(main())
```

Run it (server must be running):

```bash
uv run python client.py
```

---

## 5. Streaming

Change `ClientConfig(streaming=False)` to `streaming=True` and add `await client.close()` afterward. Each intermediate event arrives as a separate chunk:

```python
client = await create_client(
    agent=agent_card,
    client_config=ClientConfig(streaming=True),
)

async for chunk in client.send_message(request):
    print(chunk)   # prints each event as it arrives

await client.close()
```

For streaming to work, the AgentCard must declare `AgentCapabilities(streaming=True)` — the server above already does this.

---

## 6. Multi-Turn Conversations

When your agent needs clarification, it emits `input_required` instead of `completed`. The client continues the conversation using the same `taskId` and `contextId`.

**Server side** — signal you need more input:

```python
await event_queue.enqueue_event(
    TaskStatusUpdateEvent(taskId=task.id, state=TaskState.input_required)
)
```

**Client side** — send a follow-up referencing the existing task:

```python
# First turn — save the task/context IDs from the response
first_response = ...   # parse taskId and contextId from the first chunk

# Follow-up turn
follow_up = SendMessageRequest(
    message=new_text_message("USD", role=Role.ROLE_USER),
    task_id=first_response.task_id,
    context_id=first_response.context_id,
)

async for chunk in client.send_message(follow_up):
    print(chunk)
```

---

## 7. Authentication (overview)

For local testing no auth is needed. For production, security schemes are declared in the AgentCard using OpenAPI-compatible definitions and transmitted via standard HTTP headers.

| Scheme | How it works |
|--------|-------------|
| API Key | Sent in a header or query param |
| Bearer (JWT) | Client does OAuth2 client-credentials flow, sends `Authorization: Bearer <token>` |
| mTLS | Mutual TLS for high-assurance scenarios |

The client reads the auth requirements from the AgentCard, obtains credentials, and attaches them to every `SendMessage` call. The SDK handles header injection when configured.

---

## 8. Run the Official Samples

The official samples repo has more complete examples (currency converter with LangGraph, multi-agent orchestration, etc.):

```bash
git clone https://github.com/a2aproject/a2a-samples.git --depth 1
cd a2a-samples

python -m venv .venv && source .venv/bin/activate
pip install -r samples/python/requirements.txt

# Terminal 1 — start the helloworld server
python samples/python/agents/helloworld/__main__.py

# Terminal 2 — run the test client
python samples/python/agents/helloworld/test_client.py
```

Other samples to explore:

| Sample | What it demonstrates |
|--------|---------------------|
| `helloworld` | Minimal server + client |
| `langgraph` | LLM-backed agent with streaming and multi-turn |
| `human_in_the_loop` | `input_required` task state in practice |
| `multi_agent` | One A2A agent delegating to another |

---

## 9. Key Gotchas

- **`lastChunk=True` is required** on the final `TaskArtifactUpdateEvent` — omitting it leaves streaming clients hanging indefinitely.
- **`InMemoryTaskStore` is ephemeral** — task state is lost on server restart. Use `a2a-sdk[sql]` with a real DB for anything persistent.
- **AgentCard URL must match your bind address** — if you bind to `0.0.0.0` (to reach from Windows), set the AgentCard `url` to your WSL IP, not `127.0.0.1`.
- **Streaming requires declaring it** — `AgentCapabilities(streaming=True)` must be in the card or clients won't attempt SSE.
- **`contextId` vs `taskId`** — `contextId` groups multiple tasks in the same conversation thread; both are needed for multi-turn to work correctly.
- **Python 3.10+ required** — the SDK uses modern async features; check with `python --version`.

---

## 10. Further Reading

- [A2A Protocol Spec](https://a2a-protocol.org/latest/)
- [Python SDK](https://github.com/a2aproject/a2a-python)
- [Official Samples](https://github.com/a2aproject/a2a-samples)
- [Python Tutorial Series](https://a2a-protocol.org/latest/tutorials/python/1-introduction/)
- [Key Concepts](https://a2a-protocol.org/latest/topics/key-concepts/)
