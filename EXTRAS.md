# 🎁 Extras — Bonus Patterns for AgentCore Café

These are ready-to-use templates for extending Brew with additional AgentCore capabilities. Each one is a self-contained snippet you can add to your project.

---

## 🌊 Streaming Responses (WebSocket)

Brew responds token by token instead of waiting for the full response.

```python
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

agent = Agent(model=model, tools=tools, callback_handler=None)  # No callback = streaming
app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload, context):
    """Async entrypoint with yield = streaming response via WebSocket."""
    agent_stream = agent.stream_async(payload.get("prompt", ""))
    async for event in agent_stream:
        yield event  # Each token sent to client in real-time
```

Deploy with default HTTP protocol. The Runtime handles WebSocket on port 8080 at `/ws` automatically.

---

## 🌐 Browser Tool

Brew can navigate the web — search for recipes, check supplier prices, read articles.

```python
from strands import Agent
from strands_tools.browser import AgentCoreBrowser

browser_tool = AgentCoreBrowser(region="us-west-2")

agent = Agent(
    model=model,
    tools=[browser_tool.browser],
    system_prompt="You can browse the web to find coffee recipes and supplier info.",
)

response = agent("Find the best cold brew recipe on the web")
```

Requirements: `python3.11 -m pip install strands-agents-tools playwright nest-asyncio`

The browser runs in a managed Firecracker microVM. Each session is isolated. You can view live sessions in the AgentCore console.

---

## 🧠 Episodic Memory (LTM Strategy)

An additional Long-Term Memory strategy (alongside User Preferences and Semantic from Level 03). Brew captures interactions as structured episodes and generates reflections to learn patterns.

```python
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import EpisodicStrategy

memory_manager = MemoryManager(region_name="us-west-2")

memory = memory_manager.get_or_create_memory(
    name="CafeEpisodicMemory",
    strategies=[
        EpisodicStrategy(
            name="CafeEpisodes",
            namespaces=["/strategy/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}/"],
            reflection={
                "namespaces": ["/strategy/{memoryStrategyId}/actors/{actorId}/"]
            }
        )
    ]
)
```

Episodes capture: scenario, intent, actions taken, outcomes, artifacts.
Reflections extract patterns across episodes: "oat milk runs out faster on Mondays".

---

## 🤖 Multi-Agent: Agents as Tools

Split Brew into specialized agents — one for orders, one for inventory, one for reports. An orchestrator delegates.

```python
from strands import Agent

# Specialized agents
order_agent = Agent(
    model=model,
    tools=[place_order, get_menu],
    system_prompt="You handle drink orders only.",
)

inventory_agent = Agent(
    model=model,
    tools=[check_stock, restock],
    system_prompt="You manage inventory only.",
)

# Orchestrator uses agents as tools
orchestrator = Agent(
    model=model,
    tools=[order_agent.as_tool(), inventory_agent.as_tool()],
    system_prompt="You are the café manager. Delegate orders to the order agent and inventory to the inventory agent.",
)

response = orchestrator("A customer wants a latte and we need to check if we have enough milk")
```

Each agent has focused tools and prompts. The orchestrator decides who handles what.

---

## 🔗 A2A Protocol (Agent-to-Agent)

Expose Brew as an A2A server so external agents can communicate with it.

### Brew as A2A Server

```python
from strands import Agent
from strands.multiagent.a2a import A2AServer

brew = Agent(
    name="Brew the Barista",
    description="A café barista that takes orders and checks stock.",
    tools=[get_menu, place_order, check_stock],
    callback_handler=None,  # Required for A2A streaming
)

server = A2AServer(agent=brew)
server.serve()  # Starts on port 9000
```

### External agent calling Brew

```python
from strands.agent.a2a_agent import A2AAgent

# Connect to Brew's A2A server
brew_remote = A2AAgent(endpoint="http://brew-server:9000")

# Use it like a local agent
result = brew_remote("I want a mocha with oat milk")
print(result.message)
```

Deploy the A2A server on AgentCore Runtime with `--protocol A2A` in `agentcore configure`.

---

## 📡 MCP Server

Expose Brew as an MCP server so other agents or tools can discover and use his capabilities.

```bash
# Configure as MCP protocol
agentcore configure -e agent.py -n brew_mcp_server --protocol MCP

# Deploy
agentcore deploy

# Other agents connect via Gateway URL
```

Any MCP-compatible client can discover Brew's tools and invoke them.

---

## 🔒 VPC Networking

Run Brew inside your VPC to access private databases, internal APIs, or other resources.

```bash
agentcore configure -e agent.py -n brew_vpc \
  --vpc \
  --subnets subnet-0abc123,subnet-0def456 \
  --security-groups sg-0xyz789
```

Once deployed with VPC, Brew can access resources in your private subnets (RDS, ElastiCache, internal services).

---

## 🔑 Outbound Auth (access external services)

Brew accesses external services (Google Calendar, GitHub, Slack) on behalf of users.

```python
from strands import tool
from bedrock_agentcore.identity.auth import requires_access_token

@tool
@requires_access_token(
    credential_provider_name="GoogleCalendar",
    oauth_scopes=["https://www.googleapis.com/auth/calendar.readonly"],
)
def check_reservations(date: str, *, access_token: str):
    """Check café reservations for a date.
    :param date: Date to check (YYYY-MM-DD)
    """
    import requests
    resp = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"timeMin": f"{date}T00:00:00Z", "timeMax": f"{date}T23:59:59Z"},
    )
    return resp.json()
```

Setup: `agentcore identity create-credential-provider --name GoogleCalendar --type google --client-id ... --client-secret ...`

---

## 🛡️ Bedrock Guardrails

Add content filtering to Brew — block harmful content, denied topics, and PII. Guardrails are a Bedrock feature (not AgentCore-specific) that integrates directly with the model.

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    guardrail_id="your-guardrail-id",    # From Bedrock console
    guardrail_version="1",
    guardrail_trace="enabled",            # Debug info
)

agent = Agent(model=model, tools=tools)

response = agent("Tell me about Starbucks")
if response.stop_reason == "guardrail_intervened":
    print("Blocked by guardrail!")
```

Create guardrails in the Bedrock console → Guardrails → Create. Add denied topics (competitors), content filters, word filters.

---

## 📊 Structured Output

Get typed, validated responses from Brew using Pydantic models.

```python
from pydantic import BaseModel
from strands import Agent

class OrderSummary(BaseModel):
    drink: str
    size: str
    milk: str
    price: float
    confirmed: bool

agent = Agent(model=model, tools=tools)
result = agent.structured_output(
    "I want a large mocha with oat milk",
    output_model=OrderSummary,
)
print(result)  # OrderSummary(drink='Mocha', size='large', milk='oat', price=4.50, confirmed=True)
```

---

## 📚 References

- [Strands Agents — Multi-Agent Patterns](https://strandsagents.com/docs/user-guide/concepts/multi-agent/)
- [Strands Agents — A2A Protocol](https://strandsagents.com/docs/user-guide/concepts/multi-agent/agent-to-agent/)
- [Strands Agents — Structured Output](https://strandsagents.com/docs/user-guide/concepts/agents/structured-output/)
- [AgentCore Browser Quickstart](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/builtin-tools/quickstart-browser.md)
- [AgentCore Memory Strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/built-in-strategies.html)
- [AgentCore Identity — Outbound Auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- [AgentCore Runtime — VPC](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-vpc.html)
- [AgentCore Runtime — WebSocket Streaming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html)
- [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
