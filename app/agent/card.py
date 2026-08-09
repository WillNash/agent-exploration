from __future__ import annotations

import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

_agent_url = os.getenv("AGENT_URL", "http://localhost:8000/rpc")

_ENVELOPE_NOTE = (
    "Send a JSON-RPC 2.0 request to /rpc with method='SendMessage'. "
    "Place your natural-language request in params.message.parts[0].text. "
    "The agent's plain-English reply is returned in result.message.parts[0].text."
)

_AUTH_NOTE = (
    "This action requires authentication. "
    "Include a valid Bearer token in the Authorization header: "
    "'Authorization: Bearer <token>'. "
    "Obtain a token from POST /auth/login with {email, password}."
)

_list_categories_skill = AgentSkill(
    id="list_categories",
    name="List Categories",
    description=(
        "Ask the agent which product categories are available in the store. "
        "No authentication required. "
        "The agent will return a plain-English list of all categories. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=["What categories of products do you have?"],
)

_browse_skill = AgentSkill(
    id="browse_products",
    name="Browse Products",
    description=(
        "Ask the agent to list garden products, optionally filtered by category or price. "
        "No authentication required. "
        "Describe what you are looking for in plain English — the agent handles filtering. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=[
        "Show me all products.",
        "What seeds do you sell?",
        "List tools under $20.",
    ],
)

_get_product_skill = AgentSkill(
    id="get_product",
    name="Get Product",
    description=(
        "Ask the agent for details about a specific product by name or ID. "
        "No authentication required. "
        "The agent will look up the product and describe it in plain English. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=[
        "Tell me more about the trowel.",
        "What is product 3?",
    ],
)

_checkout_skill = AgentSkill(
    id="checkout",
    name="Checkout",
    description=(
        "Ask the agent to place an order for one or more products. "
        + _AUTH_NOTE + " "
        "Describe what you want to buy in plain English — the agent will look up product IDs "
        "and confirm before placing the order. "
        "Stock is decremented atomically; the agent will report any out-of-stock issues. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=[
        "I'd like to buy 2 packets of tomato seeds.",
        "Order one trowel for me.",
    ],
)

_list_purchases_skill = AgentSkill(
    id="list_purchases",
    name="List Purchases",
    description=(
        "Ask the agent to show your purchase history. "
        + _AUTH_NOTE + " "
        "The agent will return a plain-English summary of your past orders, most recent first. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    examples=["What have I ordered before?", "Show my purchase history."],
)

garden_card = AgentCard(
    name="Garden Store Agent",
    description=(
        "LLM-powered agent for the Green Thumb garden store. "
        "Accepts natural-language requests via A2A JSON-RPC and responds in plain English. "
        "To call: POST to /rpc with a JSON-RPC 2.0 envelope (method='SendMessage'), "
        "set the message role to 'ROLE_USER', and place your request in parts[0].text. "
        "The agent's plain-English reply is returned in result.message.parts[0].text. "
        "Browsing and product lookup require no authentication. "
        "Checkout and purchase history require a Bearer token obtained from POST /auth/login. "
        "Available capabilities: list categories, browse products, get product details, "
        "place orders, and view purchase history."
    ),
    version="2.0.0",
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[
        AgentInterface(
            url=_agent_url,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        )
    ],
    skills=[
        _list_categories_skill,
        _browse_skill,
        _get_product_skill,
        _checkout_skill,
        _list_purchases_skill,
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)
