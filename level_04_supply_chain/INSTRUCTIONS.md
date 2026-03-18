# 📦 Level 04: Supply Chain

## What are we building?

Brew now has a real supply chain. When you order a mocha, it actually deducts coffee beans, milk, and a cup from inventory. If stock is low, Brew warns you.

## Why does this matter?

In Levels 01-03, the menu and orders were just Python dicts in memory. Now we connect Brew to actual AWS services (DynamoDB for data, Lambda for logic) through AgentCore Gateway.

## Key concepts

- **DynamoDB:** A serverless NoSQL database. We use two tables: inventory and orders.
- **Lambda:** Serverless functions. We create two: `check_stock` (reads inventory) and `place_real_order` (deducts stock + records order).
- **AgentCore Gateway:** Converts Lambda functions into MCP tools the agent can discover and use dynamically.
- **MCP (Model Context Protocol):** A standard protocol for connecting AI agents to tools.
- **Cognito (OAuth):** Gateway uses Amazon Cognito for authentication. The setup script creates it automatically.
- **MCPClient:** A Strands component that connects to the Gateway and loads tools at startup.
- **SSM Parameter Store:** Stores Gateway URLs, Lambda ARNs, and Cognito credentials so the agent can load them without hardcoding.

## Prerequisites

- Levels 01-03 completed (agent deployed to cloud)

---

## Step 1: Create infrastructure

```bash
python3.11 level_04_supply_chain/setup_infra.py
```

This creates:
- 2 DynamoDB tables (inventory + orders) with 13 seeded items
- 2 Lambda functions (check_stock + place_order)
- 1 AgentCore Gateway with Cognito auth
- SSM parameters with all credentials
- SSM read permissions on the runtime execution role

## Step 2: Upgrade the agent

```bash
cp -f level_04_supply_chain/agent.py agent.py
agentcore deploy
```

Note: The Level 04 agent includes the memory code from Level 03 but with `MEMORY_ID = None`. If you want to keep LTM active, paste your memory ID from Level 03 into the new `agent.py`. This applies to all future levels — each `agent.py` carries forward all previous features, but optional ones (like LTM) need their IDs re-pasted after each upgrade.

## Step 3: Test

```bash
agentcore invoke '{"prompt": "How much oat milk do we have left?"}'
agentcore invoke '{"prompt": "Dame un latte grande con leche de almendras"}'
agentcore invoke '{"prompt": "Check all inventory levels"}'
```

---

## What changed?

| | Level 03 | Level 04 |
|---|---|---|
| Data | In-memory Python dicts | DynamoDB tables |
| Orders | Fake (just a receipt) | Real (deducts stock, records in DB) |
| Tools | Hardcoded in `agent_tools.py` | + Discovered dynamically via Gateway (MCP) |
| New infra | Memory | + DynamoDB + Lambda + Gateway + Cognito |
| New code | MemoryHook | + Gateway MCP connection via SSM config |

## Summary — The Adventures of Brew

<p align="center">
  <img src="comic.png" alt="Level 04 — Supply Chain" width="600">
  <br><em>Brew finally has a real kitchen — but anyone can walk in and grab whatever they want!</em>
</p>

## What's next

Level 05 adds authentication — staff can restock inventory, customers can only order.

➡️ [Go to Level 05](../level_05_identity/INSTRUCTIONS.md)

## Troubleshooting

| Error | Fix |
|---|---|
| `Gateway tools not available` | Check setup_infra.py ran successfully and SSM parameters exist |
| `AccessDeniedException: ssm:GetParameter` | Run setup_infra.py again — it adds SSM permissions to the runtime role |
| `Lambda error` | Check Lambda has DynamoDB permissions (setup_infra.py handles this) |
| `access_token error` | Cognito credentials may be wrong — check SSM parameters |
