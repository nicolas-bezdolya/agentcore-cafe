"""
AgentCore Café — Level 01: Local Barista ☕
Brew runs locally, takes orders, recommends drinks.
"""

from strands import Agent
from strands.models import BedrockModel
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


def ask(prompt):
    print(f"\n\n🗣️ Customer: {prompt}\n")
    agent(prompt)
    print()


if __name__ == "__main__":
    ask("Hola! Quiero algo con chocolate y bien fuerte")
    ask("What cold drinks do you have?")
    ask("Dame un latte grande con leche de almendras y un shot extra")
    ask("Show me the menu")
