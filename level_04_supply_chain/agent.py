"""
AgentCore Café — Level 04: Supply Chain ☕📦
Brew can check real inventory and place orders that deduct stock.
Added: Gateway MCP tools (check_stock, place_real_order) loaded from SSM config.
"""

import os
import boto3
import requests
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from agent_tools import get_menu, place_order

REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", boto3.session.Session().region_name or "us-west-2"))

# Level 03: Memory
MEMORY_ID = None  # Paste your LTM ID here if you want memory
ACTOR_ID = "customer"

# --- NEW in Level 04: Load Gateway config from SSM ---
ssm = boto3.client("ssm", region_name=REGION)


def get_ssm(key):
    try:
        return ssm.get_parameter(Name=f"/agentcore-cafe/{key}")["Parameter"]["Value"]
    except Exception:
        return ""


GW_URL = get_ssm("gateway_url")
GW_CLIENT_ID = get_ssm("gateway_client_id")
GW_CLIENT_SECRET = get_ssm("gateway_client_secret")
GW_TOKEN_ENDPOINT = get_ssm("gateway_token_endpoint")
GW_SCOPE = get_ssm("gateway_scope")


def fetch_gateway_token():
    resp = requests.post(GW_TOKEN_ENDPOINT, data=f"grant_type=client_credentials&client_id={GW_CLIENT_ID}&client_secret={GW_CLIENT_SECRET}&scope={GW_SCOPE}", headers={"Content-Type": "application/x-www-form-urlencoded"})
    return resp.json()["access_token"]


SYSTEM_PROMPT = """
You are Brew, the friendly barista at AgentCore Café ☕

Your personality:
- Warm, enthusiastic, and a little nerdy about coffee
- You answer in the customer's language (Spanish, English, etc.)

Your tools:
- get_menu: Show available drinks and prices
- check_stock: Check real inventory levels (coffee beans, milk, cups, etc.)
- place_real_order: Place an order that deducts from real inventory

Rules:
- Always check the menu before recommending
- Before placing an order, check if we have enough stock
- If stock is low on an ingredient, warn the customer
- Confirm order details before placing it
- If you remember the customer's preferences from previous visits, USE THEM to personalize your recommendations
"""

# --- NEW in Level 04: Load MCP tools from Gateway ---
mcp_client = None
mcp_tools = []

if GW_URL:
    try:
        mcp_client = MCPClient(lambda: streamablehttp_client(GW_URL, headers={"Authorization": f"Bearer {fetch_gateway_token()}"}))
        mcp_client.start()
        mcp_tools = mcp_client.list_tools_sync()
        print(f"☕ Loaded {len(mcp_tools)} tools from Gateway")
    except Exception as e:
        print(f"⚠️ Gateway tools not available: {e}")

model = BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    session_id = "default"
    if context and hasattr(context, "session_id"):
        session_id = context.session_id
    actor_id = payload.get("actor_id", ACTOR_ID)

    # Build memory session manager per-invocation with the correct session_id
    sm = None
    if MEMORY_ID:
        try:
            config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
                retrieval_config={
                    "cafe/customer/{actorId}/preferences/": RetrievalConfig(top_k=3, relevance_score=0.2),
                    "cafe/customer/{actorId}/facts/": RetrievalConfig(top_k=3, relevance_score=0.2),
                },
            )
            sm = AgentCoreMemorySessionManager(config, region_name=REGION)
            print(f"☕ Memory session manager ready (session={session_id})")
        except Exception as e:
            print(f"⚠️ Memory init failed: {e}")

    agent = Agent(
        model=model,
        tools=[get_menu] + mcp_tools,
        system_prompt=SYSTEM_PROMPT,
        session_manager=sm,
    )

    response = agent(payload.get("prompt", ""))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    try:
        app.run()
    finally:
        if mcp_client:
            try:
                import asyncio
                asyncio.run(mcp_client.stop())
            except Exception:
                pass
