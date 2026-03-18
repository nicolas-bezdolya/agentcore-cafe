# 📜 Level 08: House Rules

## What are we building?

Cedar policies on the Gateway enforce who can do what. Customers can order (max 5 drinks). Staff can check stock. Identity comes from the JWT token.

## Key concepts

- **Cedar:** Open-source policy language. `permit` and `forbid` rules.
- **Identity-based policies:** Rules based on who the user is, e.g. `principal.getTag("cognito:groups") like "*staff*"`
- **Default-deny + forbid-wins:** Everything denied unless permitted. Forbid always wins.

## Prerequisites

- Levels 01-07 completed

---

## Step 1: Setup policies

```bash
python3.11 level_08_house_rules/setup_policy.py
```

What it does:
1. Finds the existing Gateway and its targets (CheckStockTool, PlaceOrderTool)
2. Creates a Policy Engine (`agentcore_cafe_policy_engine`)
3. Creates 2 Cedar policies:
   - `permit_place_order_customers` — customers (by `cognito:groups`) can place orders
   - `permit_check_stock_staff` — only staff can check stock levels
4. Attaches the Policy Engine to the Gateway in ENFORCE mode (default-deny)
5. Adds policy permissions to the Gateway role
6. Saves the Policy Engine ID and ARN to SSM Parameter Store

## Step 2: Upgrade the agent

```bash
cp -f level_08_house_rules/agent.py agent.py
agentcore deploy
```

## Step 3: Test

If you still have `$ANA_TOKEN` and `$CARLOS_TOKEN` from Level 05, reuse them. Otherwise:

```bash
POOL_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_pool_id --query Parameter.Value --output text)
CLIENT_ID=$(aws ssm get-parameter --name /agentcore-cafe/cognito_client_id --query Parameter.Value --output text)

CARLOS_TOKEN=$(agentcore identity get-cognito-inbound-token --pool-id $POOL_ID --client-id $CLIENT_ID --username customer_carlos --password 'Coffee2026!')
ANA_TOKEN=$(agentcore identity get-cognito-inbound-token --pool-id $POOL_ID --client-id $CLIENT_ID --username barista_ana --password 'Brew2026!')
```

Test as customer Carlos:
```bash
# Carlos orders a latte and confirms (ALLOWED — customer can order via Gateway)
agentcore invoke '{"prompt": "Quiero un latte grande con leche de avena, confirmá la orden"}' --bearer-token "$CARLOS_TOKEN"

# Carlos tries to check stock (DENIED by Cedar — tool not even visible to customers)
agentcore invoke '{"prompt": "Check stock levels"}' --bearer-token "$CARLOS_TOKEN"
```

Test as staff Ana:
```bash
# Ana checks stock (ALLOWED — staff can check stock via Gateway)
agentcore invoke '{"prompt": "Cómo está el inventario?"}' --bearer-token "$ANA_TOKEN"

# Ana tries to order and confirm (DENIED by Cedar — tool not visible to staff)
agentcore invoke '{"prompt": "I want a mocha with oat milk, medium size, place the order now"}' --bearer-token "$ANA_TOKEN"
```

How to verify Cedar is working (not just the system prompt):
```bash
# Check the logs — look for how many Gateway tools each user sees
aws logs tail /aws/bedrock-agentcore/runtimes/<your-agent-id>-DEFAULT \
  --log-stream-name-prefix "YYYY/MM/DD/[runtime-logs" --since 5m \
  | grep "Gateway tools"
```

You should see:
- Carlos: `Loaded 1 Gateway tools` (only place_order — check_stock filtered by Cedar)
- Ana: `Loaded 1 Gateway tools` (only check_stock — place_order filtered by Cedar)

Cedar filters tools at the `tools/list` level — if you don't have a permit for a tool, it doesn't even appear in the agent's tool list.

Compare with previous levels: before Level 08, both Carlos and Ana could see 2 Gateway tools (check_stock + place_order). Now Cedar restricts each user to only the tools their group is permitted to use.


---

## What changed?

| | Level 07 | Level 08 |
|---|---|---|
| Rules enforcement | System prompt only (soft) | + Cedar policies on Gateway (hard, deterministic) |
| Identity in policies | — | Cedar reads `cognito:groups` from JWT token |
| New infra | — | Policy Engine, 3 Cedar policies |
| Customer access | Can see stock via Gateway | Cedar blocks `check_stock` for customers |
| Staff access | Can do everything | Cedar blocks `place_order` for staff |

## Summary — The Adventures of Brew

<p align="center">
  <img src="comic.png" alt="Level 08 — House Rules" width="600">
  <br><em>Brew keeps everyone in their lane — but is he still being a good barista?</em>
</p>

## Troubleshooting

| Error | Fix |
|---|---|
| `No Gateway found` | Run Level 04 setup first |
| `All tool calls denied` | Cedar is default-deny. Check policies were created. |
| `Policy not enforcing` | Verify ENFORCE mode in the console |
| `Identity not recognized` | Make sure Level 05 updated the Gateway authorizer |
