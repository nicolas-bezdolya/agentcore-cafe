# 📋 Level 01 — Templates

## Strands Agent (minimal)

```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

agent = Agent(
    model=model,                    # The LLM brain
    tools=[],                       # Functions the agent can call
    system_prompt="You are a helpful assistant.",  # Personality + rules
)

response = agent("Hello!")          # Send a message, get a response
print(response.message["content"][0]["text"])
```

## Custom Tool (minimal)

```python
from strands import tool

@tool
def greet(name: str):
    """Say hello to someone.
    :param name: The person's name
    """
    return f"Hello, {name}!"
```

The `@tool` decorator turns any Python function into a tool the agent can use.
The docstring becomes the tool description — the agent reads it to decide when to use it.
The `:param` lines describe each parameter.

## BedrockModel

```python
from strands.models import BedrockModel

# Use any model available in your Bedrock account
model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    # region_name="us-west-2",     # Optional: defaults to AWS_DEFAULT_REGION
    # temperature=0.7,             # Optional: creativity (0=deterministic, 1=creative)
    # max_tokens=1024,             # Optional: max response length
)
```

Available model IDs depend on your account.
