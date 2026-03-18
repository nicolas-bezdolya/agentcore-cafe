"""
AgentCore Café — Level 02: Cloud Barista ☁️
Same Brew, now deployed to AgentCore Runtime.
Added: BedrockAgentCoreApp wrapper.
"""

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_tools import get_menu, place_order

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
"""

model = BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

agent = Agent(
    model=model,
    tools=[get_menu, place_order],
    system_prompt=SYSTEM_PROMPT,
)

# --- NEW in Level 02: Cloud wrapper ---
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    response = agent(payload.get("prompt", ""))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
