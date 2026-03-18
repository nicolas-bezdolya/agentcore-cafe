# 📋 Level 03 — Templates

## Create Memory (STM — Short-Term)

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")

stm = client.create_memory_and_wait(
    name="MyAgent_STM",
    strategies=[],           # Empty = no extraction, just raw conversation
    event_expiry_days=7,     # Auto-delete after 7 days
)
print(f"Memory ID: {stm['id']}")
```

STM stores exact messages. Good for remembering within a session.

## Create Memory (LTM — Long-Term)

```python
ltm = client.create_memory_and_wait(
    name="MyAgent_LTM",
    strategies=[
        # Extracts preferences like "I prefer oat milk"
        {"userPreferenceMemoryStrategy": {
            "name": "preferences",
            "namespaces": ["cafe/customer/{actorId}/preferences/"],
        }},
        # Extracts facts like "My name is Carlos"
        {"semanticMemoryStrategy": {
            "name": "facts",
            "namespaces": ["cafe/customer/{actorId}/facts/"],
        }},
    ],
    event_expiry_days=30,
)
print(f"Memory ID: {ltm['id']}")
```

LTM automatically extracts and stores preferences/facts across sessions.
Extraction takes ~30 seconds after each conversation.

## AgentCoreMemorySessionManager (official Strands integration)

```python
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands import Agent

MEMORY_ID = "AgentCoreCafe_LTM-xxxxxxxx"

config = AgentCoreMemoryConfig(
    memory_id=MEMORY_ID,
    session_id="my-session-id",
    actor_id="carlos",
    retrieval_config={
        "cafe/customer/{actorId}/preferences/": RetrievalConfig(top_k=3, relevance_score=0.2),
        "cafe/customer/{actorId}/facts/": RetrievalConfig(top_k=3, relevance_score=0.2),
    },
)

sm = AgentCoreMemorySessionManager(config, region_name="us-east-1")

agent = Agent(
    model=model,
    tools=[get_menu, place_order],
    system_prompt="You are a helpful barista.",
    session_manager=sm,  # Handles save + retrieve + injection automatically
)

agent("I'm lactose intolerant and love mochas with almond milk")
```

The `session_manager` handles everything:
- Saves each conversation turn to STM automatically
- Retrieves relevant LTM memories before each response
- Injects memories into the agent's context so the model uses them

## SSM Parameter Store (save/load config)

```python
import boto3
ssm = boto3.client("ssm")

# Save
ssm.put_parameter(Name="/my-app/memory_id", Value="mem-abc123", Type="String", Overwrite=True)

# Load
value = ssm.get_parameter(Name="/my-app/memory_id")["Parameter"]["Value"]

# Delete
ssm.delete_parameter(Name="/my-app/memory_id")
```
