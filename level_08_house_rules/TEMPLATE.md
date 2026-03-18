# 📋 Level 08 — Templates

## Create Policy Engine

```python
import boto3
ctrl = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

engine = ctrl.create_policy_engine(
    name="my_policy_engine",
    description="My agent's access control rules",
)
engine_id = engine["policyEngineId"]
engine_arn = engine["policyEngineArn"]
```

## Create Cedar Policy (permit by identity)

```python
# Allow users in "admin" group to use a specific tool
cedar = (
    'permit(principal, '
    'action == AgentCore::Action::"TargetName___tool_name", '
    'resource == AgentCore::Gateway::"<gateway-arn>") '
    'when { principal.hasTag("cognito:groups") && '
    'principal.getTag("cognito:groups") like "*admin*" };'
)

ctrl.create_policy(
    policyEngineId=engine_id,
    name="permit_admin_tool",
    description="Only admins can use this tool",
    definition={"cedar": {"statement": cedar}},
)
```

## Create Cedar Policy (forbid by input parameter)

```python
# Deny orders with amount > 1000
cedar = (
    'forbid(principal, '
    'action == AgentCore::Action::"OrderTarget___place_order", '
    'resource == AgentCore::Gateway::"<gateway-arn>") '
    'when { context.input.amount > 1000 };'
)

ctrl.create_policy(
    policyEngineId=engine_id,
    name="forbid_large_orders",
    definition={"cedar": {"statement": cedar}},
)
```

## Attach Policy Engine to Gateway

```python
# Gateway role needs bedrock-agentcore:* permission first
ctrl.update_gateway(
    gatewayIdentifier=gateway_id,
    name=gw_name, roleArn=gw_role, protocolType="MCP",
    authorizerType="CUSTOM_JWT",
    authorizerConfiguration=gw_auth_config,
    policyEngineConfiguration={"mode": "ENFORCE", "arn": engine_arn},
    # mode: "ENFORCE" = block denied actions, "LOG_ONLY" = log but don't block
)
```

## Cedar syntax cheat sheet

```
# Permit — explicitly allow an action
permit(principal, action, resource) when { conditions };

# Forbid — explicitly deny (wins over permit)
forbid(principal, action, resource) when { conditions };

# Check JWT claim exists
principal.hasTag("claim_name")

# Match JWT claim value
principal.getTag("role") == "admin"

# Pattern match (wildcard)
principal.getTag("groups") like "*admin*"

# Input parameter check
context.input.amount <= 1000

# Multiple values
context.input.region in ["US", "CA", "UK"]

# Combined conditions
principal.hasTag("role") && principal.getTag("role") == "manager" && context.input.amount <= 10000
```

## Key concepts

- **Default-deny:** Everything is denied unless a `permit` policy allows it
- **Forbid-wins:** If any `forbid` matches, the action is denied even if a `permit` also matches
- **Action names:** Follow pattern `TargetName___tool_name` (triple underscore)
- **Principal:** Created from JWT `sub` claim. Tags come from all JWT claims.
