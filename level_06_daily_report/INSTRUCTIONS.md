# 📊 Level 06: Daily Report

## What are we building?

Brew can now write and execute Python code to generate sales charts, stock projections, and data analysis. Charts are uploaded to S3 so you can download and view them.

## Key concepts

- **AgentCore Code Interpreter:** Runs Python code in a secure sandbox. Pre-installed: pandas, matplotlib, numpy.
- **Custom Code Interpreter:** A Code Interpreter with an IAM role that has S3 permissions (PUBLIC network mode).
- **Presigned URLs:** Temporary download links for S3 objects.

## Prerequisites

- Levels 01-05 completed

---

## Step 1: Setup chart storage

```bash
python3.11 level_06_daily_report/setup_charts.py
```

What it does:
1. Creates an S3 bucket (`agentcore-cafe-charts-<account-id>`) for storing generated charts
2. Creates an IAM role (`AmazonBedrockAgentCoreCafeCharts`) with S3 put/get permissions
3. Creates a custom Code Interpreter with that role and PUBLIC network mode (so it can upload to S3)
4. Adds permissions to the Runtime execution role for the custom Code Interpreter and S3 access
5. Saves the bucket name and Code Interpreter ID to SSM Parameter Store

## Step 2: Upgrade the agent

```bash
cp -f level_06_daily_report/agent.py agent.py
agentcore deploy
```

## Step 3: Test

If you still have `$ANA_TOKEN` from Level 05, you can reuse it. Otherwise:

```bash
ANA_TOKEN=$(agentcore identity get-cognito-inbound-token \
  --pool-id $(aws ssm get-parameter --name /agentcore-cafe/cognito_pool_id --query Parameter.Value --output text) \
  --client-id $(aws ssm get-parameter --name /agentcore-cafe/cognito_client_id --query Parameter.Value --output text) \
  --username barista_ana --password 'Brew2026!')
```

```bash
# Ana generates a price chart for the daily report
agentcore invoke '{"prompt": "Create a bar chart showing the prices of all drinks on our menu"}' --bearer-token "$ANA_TOKEN"

# Ana runs a stock analysis with chart
agentcore invoke '{"prompt": "Generá un gráfico de línea mostrando cómo baja el stock de café día a día durante 30 días, empezando con 100kg y usando 2kg por día"}' --bearer-token "$ANA_TOKEN"

# Ana generates a projection chart
agentcore invoke '{"prompt": "Generate a projection chart: if we use 2kg of coffee beans per day, show stock levels for the next 30 days starting from 100kg"}' --bearer-token "$ANA_TOKEN"
```

---

---

## What changed?

| | Level 05 | Level 06 |
|---|---|---|
| New capability | Identity/access control | Code execution (charts, analysis) + S3 chart storage |
| New tool | `whoami`, `restock` | Custom `CodeInterpreterTool` with S3 access |
| New infra | Cognito User Pool | S3 bucket, IAM role, custom Code Interpreter (PUBLIC mode) |
| Staff can | Restock inventory | + Generate charts, reports, and projections |
| Customers can | Order drinks | Order drinks (no charts or internal data) |

## Summary — The Adventures of Brew

<p align="center">
  <img src="comic.png" alt="Level 06 — Daily Report" width="600">
  <br><em>Brew can crunch the numbers now — but who's going to tell him about the angry line behind him?</em>
</p>

## What's next

Level 07 adds observability — trace every order, monitor latency, and build CloudWatch dashboards.

➡️ [Go to Level 07](../level_07_observability/INSTRUCTIONS.md)

## Troubleshooting

| Error | Fix |
|---|---|
| `Code Interpreter not found` | Run `setup_charts.py` again |
| `No presigned URL` | Check SSM params exist |
| `AccessDenied on S3` | Check IAM role permissions |
