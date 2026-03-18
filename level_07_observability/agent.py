"""
AgentCore Café — Level 07: Café Dashboard ☕📈
Full observability: traces, metrics, and logs via ADOT.
"""

import os
import jwt
import json
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from agent_tools import get_menu, place_order

REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", boto3.session.Session().region_name or "us-west-2"))

# Level 03: Memory
MEMORY_ID = None
ACTOR_ID = "customer"

# Level 04: Gateway config from SSM
ssm = boto3.client("ssm", region_name=REGION)


def get_ssm(key):
    try:
        return ssm.get_parameter(Name=f"/agentcore-cafe/{key}")["Parameter"]["Value"]
    except Exception:
        return ""


GW_URL = get_ssm("gateway_url")

# Level 05: Identity config from SSM
COGNITO_POOL_ID = get_ssm("cognito_pool_id")
COGNITO_CLIENT_ID = get_ssm("cognito_client_id")
cognito_client = boto3.client("cognito-idp", region_name=REGION)
ddb_resource = boto3.resource("dynamodb", region_name=REGION)
inv_table = ddb_resource.Table("agentcore-cafe-inventory")

# Global state for current user (set in entrypoint, read by tools)
_current_user = {"username": "anonymous", "role": "customers", "groups": []}

# Level 06: Chart storage config from SSM
CHARTS_BUCKET = get_ssm("charts_bucket")
CHARTS_CI_ID = get_ssm("charts_ci_id")
s3_client = boto3.client("s3", region_name=REGION)


def get_user_from_token(token):
    """Decode JWT token (already validated by AgentCore Runtime) to get user info."""
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        username = claims.get("username", claims.get("sub", "anonymous"))
        groups = claims.get("cognito:groups", [])
        role = "staff" if "staff" in groups else "customers"
        return {"username": username, "role": role, "token": token, "groups": groups}
    except Exception as e:
        print(f"⚠️ Token decode failed: {e}")
        return {"username": "anonymous", "role": "customers", "token": token, "groups": []}


@tool
def whoami():
    """Check who is currently authenticated and their role."""
    
    if _current_user["username"] == "anonymous":
        return "No user authenticated. Pass a --bearer-token when invoking."
    emoji = "👨‍🍳" if _current_user["role"] == "staff" else "☕"
    return f"{emoji} Authenticated as {_current_user['username']} ({_current_user['role']}) — groups: {_current_user.get('groups', [])}"


@tool
def restock(item_id: str, quantity: int):
    """Restock an inventory item. Staff only.
    :param item_id: Item to restock (e.g. coffee_beans, oat_milk)
    :param quantity: How many units to add
    """
    
    if _current_user["role"] != "staff":
        return "🚫 Only staff can restock inventory. Invoke with barista_ana's token."
    try:
        inv_table.update_item(Key={"item_id": item_id}, UpdateExpression="SET stock = stock + :val", ExpressionAttributeValues={":val": quantity})
        return f"✅ Restocked {item_id} with {quantity} units."
    except Exception as e:
        return f"❌ Restock failed: {e}"


SYSTEM_PROMPT = f"""
You are Brew, the friendly barista at AgentCore Café ☕

Your personality:
- Warm, enthusiastic, and a little nerdy about coffee
- You answer in the customer's language (Spanish, English, etc.)

Your tools:
- get_menu: Show available drinks and prices
- check_stock: Check real inventory levels (via Gateway)
- place_real_order: Place an order that deducts from real inventory (via Gateway)
- whoami: Check who is currently authenticated
- restock: Add stock (staff only)
- code_interpreter: Write and execute Python code for analysis and charts

Rules:
- Always check the menu before recommending
- Before placing an order, check if we have enough stock
- If stock is low, warn the customer
- Use whoami to check who is logged in before allowing restricted actions (restock)

IMPORTANT for charts/visualizations:
- Only staff can generate charts, reports, projections, or data analysis.
- Before refusing a chart request, ALWAYS use the whoami tool first to check if the user is staff.
- If the user IS staff, proceed with generating the chart.
- If a customer asks for reports, stock projections, or internal data, politely tell them that information is only available to staff. Do NOT provide calculations, estimates, or stock numbers to customers.
- Always use matplotlib with: import matplotlib; matplotlib.use('Agg')
- After creating a chart, ALWAYS save it with: plt.savefig('chart.png', bbox_inches='tight')
- Then upload it to S3 using executeCommand with: aws s3 cp chart.png s3://{CHARTS_BUCKET}/charts/chart.png
- After uploading, tell the user the chart was saved and will be available for download
- The S3 bucket is: {CHARTS_BUCKET}
- If you remember the customer's preferences from previous visits, USE THEM to personalize your recommendations
"""


model = BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")

# Level 06: Code Interpreter
if CHARTS_CI_ID:
    code_interpreter_tool = AgentCoreCodeInterpreter(region=REGION, identifier=CHARTS_CI_ID)
    print(f"☕ Code Interpreter enabled (custom: {CHARTS_CI_ID})")
else:
    code_interpreter_tool = AgentCoreCodeInterpreter(region=REGION)
    print("☕ Code Interpreter enabled (default)")

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context=None):
    user_token = None
    current_user = {"username": "anonymous", "role": "customers", "groups": []}

    if context and hasattr(context, "request_headers"):
        auth_header = context.request_headers.get("Authorization", "")
        if auth_header:
            user_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header
            current_user = get_user_from_token(user_token)
            print(f"🔐 Authenticated: {current_user['username']} ({current_user['role']})")

    global _current_user
    _current_user = current_user

    session_id = "default"
    if context and hasattr(context, "session_id"):
        session_id = context.session_id
    actor_id = payload.get("actor_id", ACTOR_ID)

    # Build memory session manager per-invocation with the correct session_id
    sm = None
    if MEMORY_ID:
        try:
            config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id,
                retrieval_config={
                    "cafe/customer/{actorId}/preferences/": RetrievalConfig(top_k=3, relevance_score=0.2),
                    "cafe/customer/{actorId}/facts/": RetrievalConfig(top_k=3, relevance_score=0.2),
                },
            )
            sm = AgentCoreMemorySessionManager(config, region_name=REGION)
            print(f"☕ Memory session manager ready (session={session_id})")
        except Exception as e:
            print(f"⚠️ Memory init failed: {e}")

    mcp_client = None
    mcp_tools = []
    if GW_URL and user_token:
        try:
            mcp_client = MCPClient(lambda: streamablehttp_client(GW_URL, headers={"Authorization": f"Bearer {user_token}"}))
            mcp_client.start()
            mcp_tools = mcp_client.list_tools_sync()
            print(f"☕ Loaded {len(mcp_tools)} Gateway tools (as {current_user['username']})")
        except Exception as e:
            print(f"⚠️ Gateway tools not available: {e}")

    # Build tool list based on role — only staff gets code_interpreter
    tools = [get_menu, whoami, restock] + mcp_tools
    if _current_user["role"] == "staff":
        tools.append(code_interpreter_tool.code_interpreter)

    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        session_manager=sm,
    )

    response = agent(payload.get("prompt", ""))
    response_text = response.message["content"][0]["text"]

    # Generate presigned URLs for charts (only if staff used code_interpreter)
    if CHARTS_BUCKET and _current_user["role"] == "staff" and ("s3://" in response_text or "chart" in response_text.lower()):
        try:
            objs = s3_client.list_objects_v2(Bucket=CHARTS_BUCKET, Prefix="charts/")
            if objs.get("Contents"):
                latest = sorted(objs["Contents"], key=lambda x: x["LastModified"], reverse=True)[0]
                url = s3_client.generate_presigned_url("get_object", Params={"Bucket": CHARTS_BUCKET, "Key": latest["Key"]}, ExpiresIn=3600)
                response_text += f"\n\n📊 Download your chart (valid 1 hour):\n{url}"
        except Exception as e:
            print(f"⚠️ Presigned URL failed: {e}")

    if mcp_client:
        try:
            import asyncio
            asyncio.run(mcp_client.stop())
        except Exception:
            pass

    return response_text


if __name__ == "__main__":
    app.run()
