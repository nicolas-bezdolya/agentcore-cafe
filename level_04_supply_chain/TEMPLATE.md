# 📋 Level 04 — Templates

## DynamoDB Table (create)

```python
import boto3
ddb = boto3.client("dynamodb")

ddb.create_table(
    TableName="my-table",
    KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],  # Partition key
    AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],  # S=String
    BillingMode="PAY_PER_REQUEST",  # No capacity planning needed
)
```

## DynamoDB (read/write)

```python
table = boto3.resource("dynamodb").Table("my-table")

# Write
table.put_item(Item={"id": "item1", "name": "Coffee Beans", "stock": 100})

# Read
item = table.get_item(Key={"id": "item1"})["Item"]

# Update
table.update_item(
    Key={"id": "item1"},
    UpdateExpression="SET stock = stock - :val",
    ExpressionAttributeValues={":val": 1},
)

# Scan all
items = table.scan()["Items"]
```

## Lambda Function (create from code string)

```python
import boto3, zipfile, io

code = '''
import json
def handler(event, context):
    return {"statusCode": 200, "body": json.dumps({"message": "Hello!"})}
'''

# Package code as ZIP
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("lambda_function.py", code)
buf.seek(0)

lam = boto3.client("lambda")
lam.create_function(
    FunctionName="my-function",
    Runtime="python3.11",
    Role="arn:aws:iam::123456:role/MyLambdaRole",  # Must have Lambda trust policy
    Handler="lambda_function.handler",
    Code={"ZipFile": buf.read()},
    Environment={"Variables": {"TABLE_NAME": "my-table"}},
    Timeout=30,
)
```

## Lambda Execution Role

```python
import boto3, json
iam = boto3.client("iam")

iam.create_role(
    RoleName="MyLambdaRole",
    AssumeRolePolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }),
)

# Attach basic Lambda permissions (CloudWatch Logs)
iam.attach_role_policy(RoleName="MyLambdaRole", PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")
```

## AgentCore Gateway (expose Lambda as MCP tool)

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

client = GatewayClient(region_name="us-east-1")

# 1. Create OAuth authorizer (Cognito)
cognito = client.create_oauth_authorizer_with_cognito("my-gateway")

# 2. Create Gateway
gateway = client.create_mcp_gateway(
    name="my-gateway",
    role_arn="arn:aws:iam::123456:role/MyLambdaRole",
    authorizer_config=cognito["authorizer_config"],
    enable_semantic_search=True,
)

# 3. Add Lambda target with tool schema
client.create_mcp_gateway_target(
    gateway=gateway,
    name="MyTool",
    target_type="lambda",
    target_payload={
        "lambdaArn": "arn:aws:lambda:us-east-1:123456:function:my-function",
        "toolSchema": {
            "inlinePayload": [{
                "name": "my_tool",
                "description": "What this tool does",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "First parameter"},
                    },
                    "required": ["param1"],
                },
            }]
        },
    },
)

print(f"Gateway URL: {gateway['gatewayUrl']}")
```

## Connect Agent to Gateway (MCP)

```python
import requests
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

def get_token():
    resp = requests.post(TOKEN_ENDPOINT, data=f"grant_type=client_credentials&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&scope={SCOPE}", headers={"Content-Type": "application/x-www-form-urlencoded"})
    return resp.json()["access_token"]

mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL, headers={"Authorization": f"Bearer {get_token()}"}))
mcp_client.start()
tools = mcp_client.list_tools_sync()

agent = Agent(model=model, tools=tools)  # Agent now has Gateway tools
```
