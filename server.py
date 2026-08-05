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


class EchoExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        user_text = context.get_user_input()

        # Simple workflow: enqueue a single Message and return.
        # For streaming/multi-turn use TaskUpdater instead (see comment below).
        await event_queue.enqueue_event(
            new_text_message(f"Echo: {user_text}")
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise NotImplementedError


# --- TaskUpdater pattern (for streaming / long-running tasks) ---
#
# class EchoExecutor(AgentExecutor):
#     async def execute(self, context: RequestContext, event_queue: EventQueue):
#         updater = TaskUpdater(event_queue, context.task_id, context.context_id)
#         await updater.start_work()
#         user_text = context.get_user_input()
#         await updater.add_artifact(
#             parts=[new_text_part(f"Echo: {user_text}")],
#             last_chunk=True,
#         )
#         await updater.complete()


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
