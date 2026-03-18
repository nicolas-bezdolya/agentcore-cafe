"""
AgentCore Café — Level 03: Barista with Memory ☕🧠
Brew remembers customers across sessions using AgentCoreMemorySessionManager.
"""

import os
import boto3
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from agent_tools import get_menu, place_order

REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or boto3.session.Session().region_name
    or "us-west-2"
)

# --- NEW in Level 03: Memory ID (paste from setup_memory.py) ---
MEMORY_ID = None  # e.g. "AgentCoreCafe_LTM-xxxxxxxx"
ACTOR_ID = "customer"

SYSTEM_PROMPT = """
You are Brew, the friendly barista at AgentCore Café ☕

Your personality:
- Warm, enthusiastic, and a little nerdy about coffee
- You love recommending drinks based on what the customer describes
- You always suggest a pairing (cookie, muffin) without being pushy
- You answer in the customer's language (Spanish, English, etc.)

Your tools:
- get_menu: Show available drinks, filter by hot/cold
- place_order: Confirm and process a drink order

Rules:
- Always check the menu before recommending
- Confirm the order details before placing it
- If someone asks for something not on the menu, suggest the closest alternative
- If you remember the customer's preferences from previous visits, USE THEM to personalize your recommendations
"""

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
        tools=[get_menu, place_order],
        system_prompt=SYSTEM_PROMPT,
        session_manager=sm,
    )

    response = agent(payload.get("prompt", ""))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
