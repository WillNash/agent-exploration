from __future__ import annotations

import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

_agent_url = os.getenv("AGENT_URL", "http://localhost:8000/rpc")

_browse_skill = AgentSkill(
    id="browse_products",
    name="Browse Products",
    description="List garden products, optionally filtered by category or max price.",
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"browse_products","category":"seeds"}'],
)

_get_product_skill = AgentSkill(
    id="get_product",
    name="Get Product",
    description="Retrieve full details for a single product by ID.",
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"get_product","product_id":1}'],
)

_checkout_skill = AgentSkill(
    id="checkout",
    name="Checkout",
    description="Place an order for one or more products on behalf of a customer.",
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=[
        '{"action":"checkout","customer_email":"alice@example.com","items":[{"product_id":1,"quantity":2}]}'
    ],
)

_list_purchases_skill = AgentSkill(
    id="list_purchases",
    name="List Purchases",
    description="Return the purchase history for a customer by email.",
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"list_purchases","customer_email":"alice@example.com"}'],
)

garden_card = AgentCard(
    name="Garden Store Agent",
    description="Deterministic agent for the Green Thumb garden store. Accepts structured JSON intents.",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[
        AgentInterface(
            url=_agent_url,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
    skills=[_browse_skill, _get_product_skill, _checkout_skill, _list_purchases_skill],
    default_input_modes=["text/plain"],
    default_output_modes=["application/json"],
)
