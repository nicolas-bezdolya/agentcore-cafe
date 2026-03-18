# 📈 Level 07: Café Dashboard

## What are we building?

Brew now has full observability. Every order, every tool call, every model invocation is traced and visible in CloudWatch. You can see exactly what Brew is doing, how long each step takes, and where things go wrong.

## Why does this matter?

In production, you need to know what your agent is doing. If a customer complains that Brew took 10 seconds to respond, you need to see: was it the model thinking? A slow tool call? A network issue? Observability gives you that visibility.

## Key concepts

- **OpenTelemetry (OTEL):** An open-source standard for collecting traces, metrics, and logs. AgentCore uses it natively.
- **ADOT (AWS Distro for OpenTelemetry):** AWS's distribution of OpenTelemetry. When you deploy to AgentCore Runtime, ADOT auto-instruments your agent — no code changes needed.
- **Traces:** A trace follows a single request through the entire system. Each step (model call, tool use, etc.) is a "span" with timing info.
- **CloudWatch GenAI Dashboard:** A pre-built dashboard showing agent performance: latency, token usage, error rates, tool call frequency.
- **Transaction Search:** A CloudWatch feature that lets you search and filter traces. Must be enabled once per account.

## Prerequisites

- Levels 01-06 completed

---

## Step 1: Enable Transaction Search (one time per account)

This is a one-time setup. If you've already done it, skip to Step 2.

Option A — Via Console (easiest):
1. Open [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
2. In the left nav, go to **Settings** (under Setup)
3. Select the **X-Ray traces** tab
4. In **Transaction Search**, click **View settings** → **Edit**
5. Enable Transaction Search, select **For X-Ray users**, set sampling to 100%
6. Save. Wait until **Ingest OpenTelemetry spans** shows **Enabled**

Option B — Via CLI:
```bash
# Create resource policy for X-Ray to write to CloudWatch Logs
aws logs put-resource-policy \
  --policy-name TransactionSearchXRayAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "TransactionSearchXRayAccess",
      "Effect": "Allow",
      "Principal": {"Service": "xray.amazonaws.com"},
      "Action": "logs:PutLogEvents",
      "Resource": [
        "arn:aws:logs:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':log-group:aws/spans:*",
        "arn:aws:logs:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':log-group:/aws/application-signals/data:*"
      ]
    }]
  }'

# Set trace destination to CloudWatch Logs
aws xray update-trace-segment-destination --destination CloudWatchLogs
```

## Step 2: Enable tracing on the Runtime agent

This tells AgentCore to send trace spans to CloudWatch for your deployed agent.

1. Open the [Agents runtime](https://console.aws.amazon.com/bedrock-agentcore/agents) page in the AgentCore console
2. Select your agent (`agentcore_cafe_barista`)
3. In the **Tracing** pane, click **Edit**, toggle to **Enable**, click **Save**

Spans will appear in the `aws/spans` log group.

## Step 3: Upgrade the agent

```bash
cp -f level_07_observability/agent.py agent.py
cp -f level_07_observability/requirements.txt requirements.txt
agentcore deploy
```

Notice the `requirements.txt` change — this level replaces `strands-agents` with `strands-agents[otel]` and adds `aws-opentelemetry-distro`. These are what enable AgentCore Runtime to auto-instrument your agent with OpenTelemetry.

## Step 4: Generate some traffic

If you still have `$ANA_TOKEN` and `$CARLOS_TOKEN` from Level 05, reuse them. Otherwise:

```bash
POOL_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_pool_id --query Parameter.Value --output text)
CLIENT_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_client_id --query Parameter.Value --output text)

CARLOS_TOKEN=$(agentcore identity get-cognito-inbound-token \
  --pool-id $POOL_ID --client-id $CLIENT_ID \
  --username customer_carlos --password 'Coffee2026!')

ANA_TOKEN=$(agentcore identity get-cognito-inbound-token \
  --pool-id $POOL_ID --client-id $CLIENT_ID \
  --username barista_ana --password 'Brew2026!')
```

```bash
agentcore invoke '{"prompt": "Show me the menu"}' --bearer-token "$CARLOS_TOKEN"
agentcore invoke '{"prompt": "Dame un mocha grande con leche de avena"}' --bearer-token "$CARLOS_TOKEN"
agentcore invoke '{"prompt": "Cómo está el inventario?"}' --bearer-token "$ANA_TOKEN"
agentcore invoke '{"prompt": "Create a bar chart of drink prices"}' --bearer-token "$ANA_TOKEN"
```

## Step 5: View the dashboard

Open the GenAI Observability Dashboard in CloudWatch (replace `<region>` with your region):
```
https://console.aws.amazon.com/cloudwatch/home?region=<region>#gen-ai-observability/agent-core
```

What you'll see:
- **Agents View:** All your agents with session counts and metrics
- **Sessions View:** Individual conversation sessions
- **Traces View:** Detailed trace for each invocation — click to see the timeline of model calls, tool uses, and latency

You can also tail logs:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<your-agent-id>-DEFAULT --since 1h
```

---

## What changed?

| | Level 06 | Level 07 |
|---|---|---|
| Visibility | Logs only | Full traces, metrics, logs, dashboards |
| New dependency | — | `aws-opentelemetry-distro`, `strands-agents[otel]` |
| New code | — | None (auto-instrumented by AgentCore Runtime) |
| Dashboard | — | CloudWatch GenAI Observability Dashboard |

## Summary — The Adventures of Brew

<p align="center">
  <img src="comic.png" alt="Level 07 — Café Dashboard" width="600">
  <br><em>Brew can finally see what's going on — but who's making sure customers aren't sneaking into the kitchen?</em>
</p>

## What's next

Level 08 adds house rules — enforce limits with Cedar policies on the Gateway.

➡️ [Go to Level 08](../level_08_house_rules/INSTRUCTIONS.md)

## Troubleshooting

| Error | Fix |
|---|---|
| No traces in dashboard | Data takes up to 10 minutes to appear. Also check Transaction Search is enabled. |
| `aws-opentelemetry-distro` not found | Make sure it's in `requirements.txt` and you ran `agentcore deploy` |
| Traces show but no GenAI metrics | Verify `strands-agents[otel]` is in requirements (not just `strands-agents`) |
