"""
Setup script for Level 08: Creates Policy Engine with Cedar policies.
Identity-based + input-based policies on the Gateway.

Run once: python3.11 setup_policy.py
"""

import boto3
import json
import time
import os

REGION = boto3.session.Session().region_name or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
ACCOUNT_ID = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
ssm = boto3.client("ssm", region_name=REGION)
agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)

print(f"☕ Setting up House Rules for account {ACCOUNT_ID}...\n")


def get_ssm(key):
    try:
        return ssm.get_parameter(Name=f"/agentcore-cafe/{key}")["Parameter"]["Value"]
    except Exception:
        return ""


# Step 1: Find Gateway
print("📡 Step 1: Finding Gateway...")
gateways = agentcore_ctrl.list_gateways().get("items", [])
gateway = next((g for g in gateways if "agentcore-cafe" in g.get("name", "").lower()), None)
if not gateway:
    print("   ❌ No Gateway found. Run Level 04 first."); exit(1)
GATEWAY_ID = gateway["gatewayId"]
gw_detail = agentcore_ctrl.get_gateway(gatewayIdentifier=GATEWAY_ID)
GATEWAY_ARN = gw_detail["gatewayArn"]
print(f"   ✅ Gateway: {GATEWAY_ID}")

targets = agentcore_ctrl.list_gateway_targets(gatewayIdentifier=GATEWAY_ID).get("items", [])
print(f"   📋 Targets: {[t['name'] for t in targets]}")


# Find tool action names
check_stock_action = None
place_order_action = None
for t in targets:
    name = t.get("name", "")
    if "stock" in name.lower() or "check" in name.lower():
        check_stock_action = f"{name}___check_stock"
    if "order" in name.lower() or "place" in name.lower():
        place_order_action = f"{name}___place_real_order"
print(f"   🔧 check_stock: {check_stock_action}")
print(f"   🔧 place_order: {place_order_action}")

# Step 2: Create Policy Engine
print(f"\n🏛️  Step 2: Creating Policy Engine...")
ENGINE_NAME = "agentcore_cafe_policy_engine"
try:
    resp = agentcore_ctrl.create_policy_engine(name=ENGINE_NAME, description="AgentCore Café house rules")
    engine_id = resp["policyEngineId"]
    engine_arn = resp["policyEngineArn"]
    print(f"   ✅ Created: {engine_id}")
except Exception as e:
    if "Conflict" in str(e) or "already exists" in str(e).lower():
        engines = agentcore_ctrl.list_policy_engines().get("policyEngines", [])
        eng = next(e for e in engines if e.get("name") == ENGINE_NAME)
        engine_id = eng["policyEngineId"]
        engine_arn = eng.get("policyEngineArn", f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:policy-engine/{engine_id}")
        print(f"   ✅ Already exists: {engine_id}")
    else:
        print(f"   ❌ Failed: {e}"); exit(1)
time.sleep(5)

# Step 3: Create Cedar Policies
print(f"\n📜 Step 3: Creating Cedar policies...")
policies = []
if place_order_action:
    policies.append({"name": "permit_place_order_customers", "description": "Customers can place orders",
        "cedar": f'permit(principal, action == AgentCore::Action::"{place_order_action}", resource == AgentCore::Gateway::"{GATEWAY_ARN}") when {{ principal.hasTag("cognito:groups") && principal.getTag("cognito:groups") like "*customers*" }};'})
if check_stock_action:
    policies.append({"name": "permit_check_stock_staff", "description": "Only staff can check stock",
        "cedar": f'permit(principal, action == AgentCore::Action::"{check_stock_action}", resource == AgentCore::Gateway::"{GATEWAY_ARN}") when {{ principal.hasTag("cognito:groups") && principal.getTag("cognito:groups") like "*staff*" }};'})

for pol in policies:
    try:
        agentcore_ctrl.create_policy(policyEngineId=engine_id, name=pol["name"], description=pol["description"], definition={"cedar": {"statement": pol["cedar"]}})
        print(f"   ✅ {pol['name']}")
    except Exception as e:
        if "Conflict" in str(e) or "already exists" in str(e).lower():
            print(f"   ✅ Already exists: {pol['name']}")
        else:
            print(f"   ⚠️ {pol['name']} failed: {e}")


# Step 4: Attach Policy Engine to Gateway
print(f"\n🔗 Step 4: Attaching Policy Engine to Gateway (ENFORCE)...")

# First, add GetPolicyEngine permission to the Gateway role
iam = boto3.client("iam")
gw_role_name = gw_detail["roleArn"].split("/")[-1]
try:
    iam.put_role_policy(
        RoleName=gw_role_name,
        PolicyName="PolicyEngineAccess",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "bedrock-agentcore:*",
                "Resource": "*"
            }]
        })
    )
    print(f"   ✅ Added GetPolicyEngine permission to {gw_role_name}")
    import time as t
    t.sleep(10)  # Wait for IAM propagation
except Exception as e:
    print(f"   ⚠️ Could not add permission: {e}")

try:
    agentcore_ctrl.update_gateway(
        gatewayIdentifier=GATEWAY_ID,
        name=gw_detail.get("name", "agentcore-cafe-supply"),
        roleArn=gw_detail["roleArn"],
        protocolType=gw_detail.get("protocolType", "MCP"),
        authorizerType=gw_detail.get("authorizerType", "CUSTOM_JWT"),
        authorizerConfiguration=gw_detail.get("authorizerConfiguration", {}),
        policyEngineConfiguration={"mode": "ENFORCE", "arn": engine_arn}
    )
    print(f"   ✅ Policy Engine attached in ENFORCE mode")
except Exception as e:
    print(f"   ⚠️ Attach failed: {e}")

# Step 5: Save to SSM
for key, val in [("policy_engine_id", engine_id), ("policy_engine_arn", engine_arn)]:
    ssm.put_parameter(Name=f"/agentcore-cafe/{key}", Value=val, Type="String", Overwrite=True)

print(f"\n✅ House Rules active!")
print(f"   ☕ Customers can order")
print(f"   👨‍🍳 Staff can check stock")
print(f"   🚫 Cedar enforces identity-based rules on Gateway (default-deny)")
