# ⭐ Level 09: Quality Control

## What are we building?

LLM-as-Judge evaluates Brew's responses on friendliness and rule compliance. Scores appear in CloudWatch.

## Key concepts

- **AgentCore Evaluations:** Automated assessment using LLM-as-a-Judge. Currently in preview.
- **Custom Evaluator:** You define instructions, rating scale, and judge model. AgentCore runs it on each trace.
- **cafe_friendliness evaluator:** Scores how warm, welcoming, and enthusiastic Brew is. Scale: 0 (cold/rude) to 1 (very warm, uses emojis, makes customer feel welcome).
- **cafe_rule_compliance evaluator:** Scores if Brew follows the house rules: max 5 drinks, suggest food pairing, no competitors, stay professional if rude, confirm price. Scale: 0 (major violation) to 1 (all rules followed).
- **Online evaluation:** Runs continuously on live traffic. Scores appear in CloudWatch GenAI Dashboard.
- **On-demand evaluation:** Targeted assessment of specific traces. Useful for investigating issues.

## Prerequisites

- Levels 01-08 completed

---

## Step 1: Create evaluators

```bash
python3.11 level_09_evaluations/setup_evaluations.py
```

What it does:
1. Creates a `cafe_friendliness` evaluator — LLM-as-Judge scores how warm and welcoming Brew is (0-1 scale)
2. Creates a `cafe_rule_compliance` evaluator — LLM-as-Judge scores if Brew follows house rules (0-1 scale)
3. Both use Claude as the judge model with custom instructions and rating scales
4. Creates an Online Evaluation Configuration that connects the evaluators to your agent (100% sampling)
5. Saves evaluator IDs to SSM Parameter Store
6. Note: Evaluations is in preview — if the script fails, you can create the evaluation config manually from the AgentCore console → Evaluation → Create evaluation configuration

## Step 2: Generate traffic

No deploy needed — evaluations run server-side in AgentCore, not in the agent code.

If you still have `$ANA_TOKEN` and `$CARLOS_TOKEN` from Level 05, reuse them. Otherwise:

```bash
POOL_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_pool_id --query Parameter.Value --output text)
CLIENT_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_client_id --query Parameter.Value --output text)

CARLOS_TOKEN=$(agentcore identity get-cognito-inbound-token --pool-id $POOL_ID --client-id $CLIENT_ID --username customer_carlos --password 'Coffee2026!')
ANA_TOKEN=$(agentcore identity get-cognito-inbound-token --pool-id $POOL_ID --client-id $CLIENT_ID --username barista_ana --password 'Brew2026!')
```

```bash
# Friendly interaction (should score high on friendliness)
agentcore invoke '{"prompt": "Hola! Qué me recomendás para un día frío?"}' --bearer-token "$CARLOS_TOKEN"

# Competitor mention (should score low on rule compliance)
agentcore invoke '{"prompt": "Is Starbucks better?"}' --bearer-token "$CARLOS_TOKEN"

# Rude customer (should score high on friendliness if Brew stays professional)
agentcore invoke '{"prompt": "Este café es malísimo"}' --bearer-token "$CARLOS_TOKEN"

# Staff interaction
agentcore invoke '{"prompt": "Cómo está el inventario?"}' --bearer-token "$ANA_TOKEN"
```

## Step 3: View scores

Open (replace `<region>` with your region): https://console.aws.amazon.com/cloudwatch/home?region=<region>#gen-ai-observability/agent-core

---

---

## What changed?

| | Level 08 | Level 09 |
|---|---|---|
| Quality monitoring | None | LLM-as-Judge evaluations |
| New infra | Policy Engine | Custom evaluators (friendliness, rule compliance) |
| Visibility | Rules enforced but not scored | Rules enforced + quality scored continuously |

## 🎉 Congratulations!

You've completed all 9 levels of AgentCore Café!

| Level | AgentCore Service | What Brew learned |
|---|---|---|
| 01 | — | Take orders locally with Strands |
| 02 | Runtime | Deploy to the cloud |
| 03 | Memory | Remember customers |
| 04 | Gateway | Check real inventory via MCP tools |
| 05 | Identity | Authenticate staff vs customers |
| 06 | Code Interpreter | Generate charts and analysis |
| 07 | Observability | Trace every interaction |
| 08 | Policy | Enforce hard rules with Cedar |
| 09 | Evaluations | Monitor response quality |


## Summary — The Adventures of Brew

<p align="center">
  <img src="comic.png" alt="Level 09 — Quality Control" width="600">
  <br><em>Brew made it — from a simple script to a production-ready, quality-monitored AI barista. Time to celebrate!</em>
</p>

## Troubleshooting

| Error | Fix |
|---|---|
| `CreateEvaluator failed` | Evaluations may be in preview and not available in your region |
| `No scores in dashboard` | Scores take a few minutes after traffic |
| `Judge model access denied` | Ensure the judge model is enabled in Bedrock console |

➡️ [Back to README](../README.md)
