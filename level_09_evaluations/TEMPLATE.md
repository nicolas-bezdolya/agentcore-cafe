# 📋 Level 09 — Templates

## Create Custom Evaluator (LLM-as-Judge)

```python
import boto3
ctrl = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

evaluator = ctrl.create_evaluator(
    evaluatorName="my_evaluator",
    description="Evaluates response quality",
    level="TRACE",  # TRACE = per request, SESSION = per conversation, TOOL_CALL = per tool use
    evaluatorConfig={
        "llmAsAJudge": {
            "modelConfig": {
                "bedrockEvaluatorModelConfig": {
                    "modelId": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
                    "inferenceConfig": {"maxTokens": 500, "temperature": 0.0},
                }
            },
            "instructions": (
                "Evaluate the assistant's response for helpfulness and accuracy.\n\n"
                "Context: {context}\n"
                "Assistant Response: {assistant_turn}"
            ),
            "ratingScale": {
                "numerical": [
                    {"value": 1.0, "label": "Excellent", "definition": "Fully accurate and helpful"},
                    {"value": 0.5, "label": "OK", "definition": "Partially helpful"},
                    {"value": 0.0, "label": "Poor", "definition": "Unhelpful or incorrect"},
                ]
            },
        }
    },
)
evaluator_id = evaluator["evaluatorId"]
```

## Placeholders for instructions

Depending on the evaluation level, you can use these placeholders:

| Level | Available placeholders |
|---|---|
| SESSION | `{context}`, `{available_tools}` |
| TRACE | `{context}`, `{assistant_turn}` |
| TOOL_CALL | `{context}`, `{tool_turn}`, `{available_tools}` |

## Create Online Evaluation Config (continuous monitoring)

```python
from bedrock_agentcore_starter_toolkit import Evaluation

eval_client = Evaluation()

config = eval_client.create_online_config(
    config_name="my_eval_config",           # Must use underscores, not hyphens
    agent_id="my_agent-abc123",             # Agent runtime ID
    sampling_rate=100,                       # % of interactions to evaluate (1-100)
    evaluator_list=[
        evaluator_id,                        # Your custom evaluator
        "Builtin.Helpfulness",               # Built-in evaluators
        "Builtin.GoalSuccessRate",
        "Builtin.Correctness",
    ],
    config_description="My agent quality monitoring",
    auto_create_execution_role=True,         # Creates IAM role automatically
    enable_on_create=True,                   # Start evaluating immediately
)
```

## Built-in evaluators

| Evaluator | What it measures |
|---|---|
| `Builtin.Helpfulness` | How helpful the response is |
| `Builtin.GoalSuccessRate` | Whether the agent achieved the user's goal |
| `Builtin.Correctness` | Factual accuracy of the response |
| `Builtin.ToolSelectionAccuracy` | Whether the agent chose the right tool |
| `Builtin.ToolParameterAccuracy` | Whether tool parameters were correct |

## View results

Results appear in:
- CloudWatch GenAI Observability Dashboard → Evaluations tab
- CloudWatch Metrics → `Bedrock-AgentCore/Evaluations` namespace
- CloudWatch Logs → `/aws/bedrock-agentcore/evaluations/results/<config-id>`

Note: Results may take 15+ minutes to appear (sessions must close before evaluation).
