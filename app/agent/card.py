from __future__ import annotations

import os

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

_agent_url = os.getenv("AGENT_URL", "http://localhost:8000/rpc")

_ENVELOPE_NOTE = (
    "Send a JSON-RPC 2.0 request to /rpc with method='SendMessage'. "
    "The agent's reply is in result.message.parts[0].text as a JSON string. "
    "Parse that string to get the structured response."
)

_list_categories_skill = AgentSkill(
    id="list_categories",
    name="List Categories",
    description=(
        "Return all distinct product categories available in the store. "
        "No parameters required. "
        "Response: JSON array of strings, e.g. [\"seeds\", \"tools\", \"pots\"]. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"list_categories"}'],
)

_browse_skill = AgentSkill(
    id="browse_products",
    name="Browse Products",
    description=(
        "List garden products, optionally filtered by category or maximum price. "
        "Intent schema: {\"action\":\"browse_products\", \"category\":\"string (optional)\", \"max_price\":\"number (optional)\"}. "
        "Response: array of product objects each with fields: id, name, description, price (float), category, stock_qty. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=[
        '{"action":"browse_products"}',
        '{"action":"browse_products","category":"seeds"}',
        '{"action":"browse_products","max_price":10.00}',
    ],
)

_get_product_skill = AgentSkill(
    id="get_product",
    name="Get Product",
    description=(
        "Retrieve full details for a single product by its integer ID. "
        "Intent schema: {\"action\":\"get_product\", \"product_id\":\"integer (required)\"}. "
        "Response: product object with fields: id, name, description, price (float), category, stock_qty. "
        "Returns {\"error\":\"product_not_found\"} if the ID does not exist. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"get_product","product_id":1}'],
)

_create_customer_skill = AgentSkill(
    id="create_customer",
    name="Create Customer",
    description=(
        "Register a new customer or update the name of an existing customer by email. "
        "This is idempotent: calling it again with the same email updates the stored name. "
        "Must be called before checkout if the customer does not already exist. "
        "Intent schema: {\"action\":\"create_customer\", \"name\":\"string (required)\", \"email\":\"string (required)\"}. "
        "Response: customer object with fields: id, name, email, created_at. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"create_customer","name":"Alice Green","email":"alice@example.com"}'],
)

_checkout_skill = AgentSkill(
    id="checkout",
    name="Checkout",
    description=(
        "Place an order for one or more products on behalf of an existing customer. "
        "The customer must exist — call create_customer first if needed. "
        "Decrements stock atomically; returns an error if any item is out of stock. "
        "Intent schema: {\"action\":\"checkout\", \"customer_email\":\"string (required)\", "
        "\"items\":[{\"product_id\":\"integer\",\"quantity\":\"integer\"}] (required, non-empty)}. "
        "Response on success: {\"status\":\"confirmed\", \"customer_email\":\"...\", "
        "\"items\":[{\"purchase_id\", \"product_id\", \"product_name\", \"quantity\", \"unit_price\", \"line_total\"}], "
        "\"order_total\":\"float\"}. "
        "Error responses: {\"error\":\"customer_not_found\"} or {\"error\":\"insufficient_stock\", \"available\":N}. "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=[
        '{"action":"checkout","customer_email":"alice@example.com","items":[{"product_id":1,"quantity":2}]}'
    ],
)

_list_purchases_skill = AgentSkill(
    id="list_purchases",
    name="List Purchases",
    description=(
        "Return the full purchase history for a customer, most recent first. "
        "Returns an empty array if the email is not found (no error). "
        "Intent schema: {\"action\":\"list_purchases\", \"customer_email\":\"string (required)\"}. "
        "Response: array of purchase objects each with fields: id, customer_id, product_id, product_name, price (float), quantity, purchased_at (ISO-8601). "
        + _ENVELOPE_NOTE
    ),
    input_modes=["text/plain"],
    output_modes=["application/json"],
    examples=['{"action":"list_purchases","customer_email":"alice@example.com"}'],
)

garden_card = AgentCard(
    name="Garden Store Agent",
    description=(
        "Deterministic agent for the Green Thumb garden store. "
        "Accepts structured JSON intents sent as plain text via A2A JSON-RPC. "
        "To call: POST to /rpc with a JSON-RPC 2.0 envelope (method='SendMessage'), "
        "set the message role to 'ROLE_USER', and place your JSON intent in parts[0].text. "
        "The agent's JSON response is returned in result.message.parts[0].text — parse it to get the structured data. "
        "Available actions: list_categories, browse_products, get_product, create_customer, checkout, list_purchases. "
        "For unknown actions the agent returns {\"error\":\"unknown_intent\", \"help\":{...}} listing all supported actions."
    ),
    version="1.0.0",
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
        _create_customer_skill,
        _checkout_skill,
        _list_purchases_skill,
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["application/json"],
)
