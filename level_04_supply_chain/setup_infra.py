"""
AgentCore Café — Level 04: Setup Infrastructure ☕📦
Creates DynamoDB tables, Lambda functions, and AgentCore Gateway.

This script sets up the "supply chain" for the café:
- A DynamoDB table with inventory (coffee beans, milk, cups, etc.)
- A DynamoDB table with orders history
- Lambda functions that read/write to those tables
- An AgentCore Gateway that exposes those Lambdas as MCP tools

After running this, Brew can check stock levels and process real orders.
"""

import json
import time
import boto3
import uuid

region = boto3.session.Session().region_name or "us-west-2"
account_id = boto3.client("sts").get_caller_identity()["Account"]
ssm = boto3.client("ssm", region_name=region)
ddb = boto3.client("dynamodb", region_name=region)
lam = boto3.client("lambda", region_name=region)
iam = boto3.client("iam")

INVENTORY_TABLE = "agentcore-cafe-inventory"
ORDERS_TABLE = "agentcore-cafe-orders"
PREFIX = "/agentcore-cafe"


def save_ssm(key, value):
    ssm.put_parameter(Name=f"{PREFIX}/{key}", Value=value, Type="String", Overwrite=True)
    print(f"💾 SSM: {PREFIX}/{key}")


# ============================================================
# Step 1: DynamoDB Tables
# ============================================================
print("☕ Step 1: Creating DynamoDB tables...\n")

for table_name, pk in [(INVENTORY_TABLE, "item_id"), (ORDERS_TABLE, "order_id")]:
    try:
        ddb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": pk, "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Created table: {table_name}")
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
    except ddb.exceptions.ResourceInUseException:
        print(f"☕ Table {table_name} already exists")

# Seed inventory
print("\n📦 Seeding inventory...")
ddb_resource = boto3.resource("dynamodb", region_name=region)
inv_table = ddb_resource.Table(INVENTORY_TABLE)

inventory_items = [
    {"item_id": "coffee_beans", "name": "Coffee Beans", "stock": 100, "unit": "kg", "min_stock": 10},
    {"item_id": "whole_milk", "name": "Whole Milk", "stock": 50, "unit": "liters", "min_stock": 5},
    {"item_id": "oat_milk", "name": "Oat Milk", "stock": 30, "unit": "liters", "min_stock": 5},
    {"item_id": "almond_milk", "name": "Almond Milk", "stock": 25, "unit": "liters", "min_stock": 5},
    {"item_id": "soy_milk", "name": "Soy Milk", "stock": 20, "unit": "liters", "min_stock": 5},
    {"item_id": "chocolate", "name": "Chocolate Syrup", "stock": 15, "unit": "liters", "min_stock": 3},
    {"item_id": "vanilla_syrup", "name": "Vanilla Syrup", "stock": 10, "unit": "liters", "min_stock": 2},
    {"item_id": "caramel_syrup", "name": "Caramel Syrup", "stock": 10, "unit": "liters", "min_stock": 2},
    {"item_id": "cups_small", "name": "Small Cups", "stock": 200, "unit": "units", "min_stock": 50},
    {"item_id": "cups_medium", "name": "Medium Cups", "stock": 200, "unit": "units", "min_stock": 50},
    {"item_id": "cups_large", "name": "Large Cups", "stock": 150, "unit": "units", "min_stock": 50},
    {"item_id": "cookies", "name": "Chocolate Chip Cookies", "stock": 40, "unit": "units", "min_stock": 10},
    {"item_id": "muffins", "name": "Blueberry Muffins", "stock": 30, "unit": "units", "min_stock": 10},
]

for item in inventory_items:
    inv_table.put_item(Item=item)
print(f"✅ Seeded {len(inventory_items)} inventory items")

# ============================================================
# Step 2: Lambda Execution Role
# ============================================================
print("\n☕ Step 2: Creating Lambda execution role...\n")

LAMBDA_ROLE_NAME = "AgentCoreCafe-LambdaRole"

lambda_trust = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"},
        {"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole",
         "Condition": {"StringEquals": {"aws:SourceAccount": account_id}, "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"}}},
    ],
}

try:
    role_resp = iam.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(lambda_trust),
        Description="Lambda role for AgentCore Café supply chain",
    )
    lambda_role_arn = role_resp["Role"]["Arn"]
    print(f"✅ Created role: {LAMBDA_ROLE_NAME}")

    # Attach basic Lambda + DynamoDB permissions
    iam.attach_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")
    iam.put_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyName="DynamoDBAccess",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "dynamodb:*", "Resource": f"arn:aws:dynamodb:{region}:{account_id}:table/agentcore-cafe-*"}],
        }),
    )
    print("✅ Attached DynamoDB + CloudWatch policies")
    print("⏳ Waiting 10s for IAM propagation...")
    time.sleep(10)
except iam.exceptions.EntityAlreadyExistsException:
    lambda_role_arn = f"arn:aws:iam::{account_id}:role/{LAMBDA_ROLE_NAME}"
    print(f"☕ Role {LAMBDA_ROLE_NAME} already exists")

save_ssm("lambda_role_arn", lambda_role_arn)

# ============================================================
# Step 3: Lambda Functions
# ============================================================
print("\n☕ Step 3: Creating Lambda functions...\n")

# --- check_stock Lambda ---
check_stock_code = '''
import json, boto3, os
ddb = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    item_id = event.get("item_id", "")
    if item_id:
        resp = ddb.get_item(Key={"item_id": item_id})
        item = resp.get("Item")
        if not item:
            return {"error": f"Item {item_id} not found"}
        return {"item_id": item["item_id"], "name": item["name"], "stock": int(item["stock"]), "unit": item["unit"], "low_stock": int(item["stock"]) <= int(item["min_stock"])}
    else:
        items = ddb.scan()["Items"]
        return [{"item_id": i["item_id"], "name": i["name"], "stock": int(i["stock"]), "unit": i["unit"], "low_stock": int(i["stock"]) <= int(i["min_stock"])} for i in items]
'''

# --- place_order Lambda ---
place_order_code = '''
import json, boto3, os, uuid
from datetime import datetime
inv = boto3.resource("dynamodb").Table(os.environ["INVENTORY_TABLE"])
orders = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE"])

def handler(event, context):
    drink = event.get("drink_name", "")
    size = event.get("size", "medium")
    milk = event.get("milk_type", "whole")
    if not drink:
        return {"error": "drink_name required"}

    try:
        inv.update_item(Key={"item_id": "coffee_beans"}, UpdateExpression="SET stock = stock - :val", ExpressionAttributeValues={":val": 1})
        cup_key = f"cups_{size}"
        inv.update_item(Key={"item_id": cup_key}, UpdateExpression="SET stock = stock - :val", ExpressionAttributeValues={":val": 1})
        milk_key = {"whole": "whole_milk", "oat": "oat_milk", "almond": "almond_milk", "soy": "soy_milk"}.get(milk, "whole_milk")
        inv.update_item(Key={"item_id": milk_key}, UpdateExpression="SET stock = stock - :val", ExpressionAttributeValues={":val": 1})
    except Exception as e:
        return {"error": f"Stock update failed: {str(e)}"}

    order = {"order_id": str(uuid.uuid4())[:8], "drink": drink, "size": size, "milk": milk, "timestamp": datetime.utcnow().isoformat(), "status": "confirmed"}
    orders.put_item(Item=order)
    return order
'''

import zipfile, io

def create_lambda(name, code, env_vars):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("lambda_function.py", code)
    buf.seek(0)

    try:
        lam.create_function(
            FunctionName=name,
            Runtime="python3.11",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": buf.read()},
            Environment={"Variables": env_vars},
            Timeout=30,
        )
        print(f"✅ Created Lambda: {name}")
    except lam.exceptions.ResourceConflictException:
        print(f"☕ Lambda {name} already exists, updating...")
        buf.seek(0)
        lam.update_function_code(FunctionName=name, ZipFile=buf.read())

    arn = f"arn:aws:lambda:{region}:{account_id}:function:{name}"
    return arn

check_stock_arn = create_lambda("agentcore-cafe-check-stock", check_stock_code, {"TABLE_NAME": INVENTORY_TABLE})
place_order_arn = create_lambda("agentcore-cafe-place-order", place_order_code, {"INVENTORY_TABLE": INVENTORY_TABLE, "ORDERS_TABLE": ORDERS_TABLE})

save_ssm("check_stock_lambda_arn", check_stock_arn)
save_ssm("place_order_lambda_arn", place_order_arn)

# ============================================================
# Step 4: AgentCore Gateway
# ============================================================
print("\n☕ Step 4: Creating AgentCore Gateway...\n")

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

gw_client = GatewayClient(region_name=region)

# Check if Gateway already exists and SSM config is complete
existing_gateway = None
try:
    gw_result = gw_client.list_gateways()
    for g in gw_result.get("items", []):
        if "agentcore-cafe-supply" in g.get("name", ""):
            existing_gateway = gw_client.get_gateway(g["gatewayId"])
            break
except Exception:
    pass

gateway_already_configured = False
if existing_gateway:
    try:
        ssm.get_parameter(Name=f"{PREFIX}/gateway_client_id")
        gateway_already_configured = True
    except Exception:
        pass

if gateway_already_configured:
    gateway = existing_gateway
    print(f"☕ Gateway already exists: {gateway.get('gatewayUrl', '')}")
    print("☕ SSM config present, skipping Gateway setup")
else:
    # Create Cognito authorizer for the gateway
    print("🔐 Creating Cognito authorizer...")
    cognito_resp = gw_client.create_oauth_authorizer_with_cognito("agentcore-cafe")

    # Define Lambda tools schema
    lambda_config = {
        "arn": check_stock_arn,
        "tools": [
            {
                "name": "check_stock",
                "description": "Check inventory stock levels. Call with no arguments to see all items, or with item_id to check a specific item.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string", "description": "Optional item ID (e.g. coffee_beans, oat_milk, cups_large). Omit to see all items."}
                    },
                },
            },
        ],
    }

    place_order_config = {
        "arn": place_order_arn,
        "tools": [
            {
                "name": "place_real_order",
                "description": "Place a real order that deducts from inventory and records in the orders table.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "drink_name": {"type": "string", "description": "Name of the drink (e.g. Mocha, Latte, Cold Brew)"},
                        "size": {"type": "string", "description": "small, medium, or large"},
                        "milk_type": {"type": "string", "description": "whole, oat, almond, or soy"},
                    },
                    "required": ["drink_name"],
                },
            },
        ],
    }

    print("🌐 Creating Gateway...")
    try:
        gateway = gw_client.create_mcp_gateway(
            name="agentcore-cafe-supply",
            role_arn=lambda_role_arn,
            authorizer_config=cognito_resp["authorizer_config"],
            enable_semantic_search=True,
        )
    except Exception as e:
        if "already exists" in str(e).lower() or "ConflictException" in str(type(e).__name__):
            print("☕ Gateway already exists, fetching...")
            gw_result2 = gw_client.list_gateways()
            gateway = None
            for g in gw_result2.get("items", []):
                if "agentcore-cafe-supply" in g.get("name", ""):
                    gateway = gw_client.get_gateway(g["gatewayId"])
                    break
            if not gateway:
                raise Exception("Gateway exists but could not be found")
        else:
            raise

    # Fix IAM permissions for the gateway
    print("🔐 Fixing IAM permissions...")
    gw_client.fix_iam_permissions(gateway)

    # Restore Lambda trust policy (fix_iam_permissions may overwrite it)
    iam.update_assume_role_policy(
        RoleName=LAMBDA_ROLE_NAME,
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"},
                {"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole",
                 "Condition": {"StringEquals": {"aws:SourceAccount": account_id}, "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"}}},
            ],
        }),
    )
    print("✅ Restored Lambda + AgentCore trust policy")

    # Add Lambda invoke permission to the Gateway's execution role
    gateway_role_arn = gateway.get("roleArn", gateway.get("executionRoleArn", ""))
    if gateway_role_arn:
        gateway_role_name = gateway_role_arn.split("/")[-1]
        iam.put_role_policy(
            RoleName=gateway_role_name,
            PolicyName="LambdaInvokeAccess",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": "lambda:InvokeFunction",
                    "Resource": [check_stock_arn, place_order_arn],
                }],
            }),
        )
        print(f"✅ Added Lambda invoke permission to {gateway_role_name}")

    import time
    print("⏳ Waiting 30s for IAM propagation...")
    time.sleep(30)

    # Add Lambda targets
    gw_client.create_mcp_gateway_target(
        gateway=gateway,
        name="CheckStockTool",
        target_type="lambda",
        target_payload={
            "lambdaArn": check_stock_arn,
            "toolSchema": {"inlinePayload": lambda_config["tools"]},
        },
    )

    gw_client.create_mcp_gateway_target(
        gateway=gateway,
        name="PlaceOrderTool",
        target_type="lambda",
        target_payload={
            "lambdaArn": place_order_arn,
            "toolSchema": {"inlinePayload": place_order_config["tools"]},
        },
    )

    gateway_url = gateway.get("gatewayUrl", "")
    print(f"✅ Gateway URL: {gateway_url}")

    # Save gateway config to SSM
    save_ssm("gateway_url", gateway_url)
    save_ssm("gateway_client_id", cognito_resp["client_info"]["client_id"])
    save_ssm("gateway_client_secret", cognito_resp["client_info"]["client_secret"])
    save_ssm("gateway_token_endpoint", cognito_resp["client_info"]["token_endpoint"])
    save_ssm("gateway_scope", cognito_resp["client_info"]["scope"])

gateway_url = gateway.get("gatewayUrl", "")

print("\n" + "=" * 50)
print("✅ Supply chain infrastructure ready!")
print(f"   Inventory table: {INVENTORY_TABLE}")
print(f"   Orders table: {ORDERS_TABLE}")
print(f"   Check stock Lambda: {check_stock_arn}")
print(f"   Place order Lambda: {place_order_arn}")
print(f"   Gateway URL: {gateway_url}")
print("=" * 50)

# Add SSM read permission to the runtime execution role (so agent can load Gateway config)
print("\n🔐 Adding SSM permissions to runtime execution role...")
try:
    runtime_role_name = None
    # First: get role from actual agent runtime (most reliable)
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
    # Fallback: apply to ALL matching roles (covers edge cases with multiple roles)
    if not runtime_role_name:
        for page in iam.get_paginator("list_roles").paginate():
            for role in page["Roles"]:
                if role["RoleName"].startswith("AmazonBedrockAgentCoreSDKRuntime"):
                    runtime_role_name = role["RoleName"]
                    break
            if runtime_role_name:
                break

    if runtime_role_name:
        iam.put_role_policy(
            RoleName=runtime_role_name,
            PolicyName="SSMReadAccess",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": "ssm:GetParameter",
                    "Resource": f"arn:aws:ssm:{region}:{account_id}:parameter/agentcore-cafe/*",
                }],
            }),
        )
        print(f"✅ Added SSM read permission to {runtime_role_name}")
    else:
        print("⚠️ Runtime role not found — deploy the agent first, then re-run this script")
except Exception as e:
    print(f"⚠️ Could not add SSM permissions: {e}")
