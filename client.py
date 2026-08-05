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