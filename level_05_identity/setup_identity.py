"""
AgentCore Café — Level 05: Setup Identity ☕🔐
Creates Cognito User Pool with two groups: staff and customers.
Updates the Gateway to accept user tokens (JWT auth).

Staff can restock inventory and check stock.
Customers can only place orders.
"""

import json
import time
import boto3

region = boto3.session.Session().region_name or "us-west-2"
account_id = boto3.client("sts", region_name=region).get_caller_identity()["Account"]
cognito = boto3.client("cognito-idp", region_name=region)
ssm = boto3.client("ssm", region_name=region)
iam = boto3.client("iam")
agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name=region)
PREFIX = "/agentcore-cafe"


def save_ssm(key, value):
    ssm.put_parameter(Name=f"{PREFIX}/{key}", Value=value, Type="String", Overwrite=True)
    print(f"💾 SSM: {PREFIX}/{key}")


def get_ssm(key):
    try:
        return ssm.get_parameter(Name=f"{PREFIX}/{key}")["Parameter"]["Value"]
    except Exception:
        return ""


print(f"☕ Setting up Identity for AgentCore Café (account {account_id})...\n")

# ============================================================
# Step 1: Create Cognito User Pool with users and groups
# ============================================================
print("🔐 Step 1: Creating Cognito User Pool...")

try:
    pool = cognito.create_user_pool(
        PoolName="AgentCoreCafe-Users",
        AutoVerifiedAttributes=["email"],
        Schema=[{"Name": "role", "AttributeDataType": "String", "Mutable": True}],
    )
    pool_id = pool["UserPool"]["Id"]
    print(f"   ✅ User Pool created: {pool_id}")
except Exception as e:
    if "exists" in str(e).lower():
        pools = cognito.list_user_pools(MaxResults=20)["UserPools"]
        pool_id = next(p["Id"] for p in pools if "AgentCoreCafe" in p["Name"])
        print(f"   ✅ User Pool already exists: {pool_id}")
    else:
        raise

for group_name, desc in [("staff", "Café staff — can restock and check stock"), ("customers", "Café customers — can place orders")]:
    try:
        cognito.create_group(GroupName=group_name, UserPoolId=pool_id, Description=desc)
        print(f"   ✅ Group: {group_name}")
    except cognito.exceptions.GroupExistsException:
        print(f"   ✅ Group already exists: {group_name}")

users = [("barista_ana", "staff", "Brew2026!"), ("customer_carlos", "customers", "Coffee2026!")]
for username, group, pwd in users:
    try:
        cognito.admin_create_user(UserPoolId=pool_id, Username=username, TemporaryPassword=pwd, MessageAction="SUPPRESS")
        cognito.admin_set_user_password(UserPoolId=pool_id, Username=username, Password=pwd, Permanent=True)
    except cognito.exceptions.UsernameExistsException:
        pass
    try:
        cognito.admin_add_user_to_group(UserPoolId=pool_id, Username=username, GroupName=group)
    except Exception:
        pass
    print(f"   ✅ User: {username} ({group}) — password: {pwd}")

try:
    app_client = cognito.create_user_pool_client(
        UserPoolId=pool_id,
        ClientName="AgentCoreCafe-UserAuth",
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        GenerateSecret=False,
    )
    user_client_id = app_client["UserPoolClient"]["ClientId"]
    print(f"   ✅ User Auth Client: {user_client_id}")
except Exception as e:
    clients = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=10)["UserPoolClients"]
    user_client_id = next((c["ClientId"] for c in clients if "UserAuth" in c.get("ClientName", "")), clients[0]["ClientId"])
    print(f"   ✅ User Auth Client already exists: {user_client_id}")

DISCOVERY_URL = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
save_ssm("cognito_pool_id", pool_id)
save_ssm("cognito_client_id", user_client_id)
save_ssm("cognito_discovery_url", DISCOVERY_URL)


# ============================================================
# Step 2: Update Gateway to accept user tokens
# ============================================================
print(f"\n🌐 Step 2: Updating Gateway authorizer to use Identity Cognito...")

gateways = agentcore_ctrl.list_gateways().get("items", [])
gateway = None
for g in gateways:
    if "agentcore-cafe" in g.get("name", "").lower():
        gateway = g
        break

if gateway:
    gw_id = gateway["gatewayId"]
    gw_detail = agentcore_ctrl.get_gateway(gatewayIdentifier=gw_id)
    try:
        agentcore_ctrl.update_gateway(
            gatewayIdentifier=gw_id,
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": DISCOVERY_URL,
                    "allowedClients": [user_client_id],
                }
            },
            name=gw_detail.get("name", "agentcore-cafe-supply"),
            roleArn=gw_detail["roleArn"],
            protocolType=gw_detail.get("protocolType", "MCP"),
        )
        print(f"   ✅ Gateway {gw_id} now accepts user tokens from {pool_id}")
    except Exception as e:
        print(f"   ⚠️ Gateway update failed: {e}")
else:
    print("   ⚠️ No Gateway found — run Level 04 setup first")

# ============================================================
# Step 3: Add permissions to Runtime execution role
# ============================================================
print(f"\n🔑 Step 3: Adding permissions to Runtime execution role...")
try:
    runtime_role_name = None
    # First: get role from actual agent runtime
    try:
        ac = boto3.client("bedrock-agentcore-control", region_name=region)
        for a in ac.list_agent_runtimes().get("agentRuntimes", []):
            if "agentcore_cafe" in a.get("agentRuntimeName", ""):
                detail = ac.get_agent_runtime(agentRuntimeId=a["agentRuntimeId"])
                role_arn = detail.get("roleArn", detail.get("executionRoleArn", ""))
                if role_arn:
                    runtime_role_name = role_arn.split("/")[-1]
                    break
    except Exception:
        pass
    # Fallback: search IAM roles
    if not runtime_role_name:
        for page in iam.get_paginator("list_roles").paginate():
            for role in page["Roles"]:
                if role["RoleName"].startswith("AmazonBedrockAgentCoreSDKRuntime"):
                    runtime_role_name = role["RoleName"]
                    break
            if runtime_role_name:
                break
    if runtime_role_name:
        iam.put_role_policy(RoleName=runtime_role_name, PolicyName="CognitoAccess",
            PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["cognito-idp:InitiateAuth", "cognito-idp:AdminListGroupsForUser", "cognito-idp:AdminGetUser"], "Resource": "*"}]}))
        iam.put_role_policy(RoleName=runtime_role_name, PolicyName="DynamoDBAccess",
            PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "dynamodb:*", "Resource": f"arn:aws:dynamodb:{region}:{account_id}:table/agentcore-cafe-*"}]}))
        print(f"   ✅ Added Cognito + DynamoDB permissions to {runtime_role_name}")
    else:
        print("   ⚠️ Runtime role not found — deploy the agent first, then re-run")
except Exception as e:
    print(f"   ⚠️ Could not add permissions: {e}")

print(f"\n{'=' * 55}")
print("✅ Identity setup complete!")
print(f"   Pool ID: {pool_id}")
print(f"   Client ID: {user_client_id}")
print(f"   👨‍🍳 barista_ana (staff) — Brew2026!")
print(f"   ☕ customer_carlos (customers) — Coffee2026!")
print(f"   Gateway updated to accept user tokens")
print(f"{'=' * 55}")
