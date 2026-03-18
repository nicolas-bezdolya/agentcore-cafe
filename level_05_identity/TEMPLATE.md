# 📋 Level 05 — Templates

## Cognito User Pool with groups and users

```python
import boto3
cognito = boto3.client("cognito-idp")

# Create pool
pool = cognito.create_user_pool(PoolName="MyApp-Users", AutoVerifiedAttributes=["email"])
pool_id = pool["UserPool"]["Id"]

# Create groups
cognito.create_group(GroupName="admin", UserPoolId=pool_id)
cognito.create_group(GroupName="users", UserPoolId=pool_id)

# Create user with permanent password
cognito.admin_create_user(UserPoolId=pool_id, Username="john", TemporaryPassword="TempPass1!", MessageAction="SUPPRESS")
cognito.admin_set_user_password(UserPoolId=pool_id, Username="john", Password="MyPass2024!", Permanent=True)
cognito.admin_add_user_to_group(UserPoolId=pool_id, Username="john", GroupName="admin")

# App client (for user auth)
app = cognito.create_user_pool_client(UserPoolId=pool_id, ClientName="MyApp",
    ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"], GenerateSecret=False)
client_id = app["UserPoolClient"]["ClientId"]
```

## Update Gateway authorizer to use your Cognito

```python
discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

agentcore_ctrl.update_gateway(
    gatewayIdentifier=gateway_id,
    authorizerType="CUSTOM_JWT",
    authorizerConfiguration={"customJWTAuthorizer": {"discoveryUrl": discovery_url, "allowedClients": [client_id]}},
    name=gw_name, roleArn=gw_role, protocolType="MCP",
)
```

## Configure Runtime with JWT Inbound Auth (CLI)

```bash
agentcore configure -e agent.py -n my_agent \
  --authorizer-config '{"customJWTAuthorizer":{"discoveryUrl":"'$DISCOVERY_URL'","allowedClients":["'$CLIENT_ID'"]}}' \
  --request-header-allowlist "Authorization" --non-interactive
```

## Get bearer token and invoke (CLI)

```bash
TOKEN=$(agentcore identity get-cognito-inbound-token \
  --pool-id $POOL_ID --client-id $CLIENT_ID \
  --username john --password 'MyPass2024!')

agentcore invoke '{"prompt": "Hello"}' --bearer-token "$TOKEN"
```

## Read JWT claims in agent code

```python
import jwt

@app.entrypoint
def invoke(payload, context=None):
    auth_header = context.request_headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    claims = jwt.decode(token, options={"verify_signature": False})
    username = claims.get("username", "anonymous")
    groups = claims.get("cognito:groups", [])
```
