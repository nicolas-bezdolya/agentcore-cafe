# 📋 Level 06 — Templates

## Custom Code Interpreter with S3 access

```python
import boto3

agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

# Create with PUBLIC mode (allows S3 access)
ci = agentcore_ctrl.create_code_interpreter(
    name="my_code_interpreter",
    description="Code interpreter with S3 access",
    executionRoleArn="arn:aws:iam::123456:role/MyCodeInterpreterRole",
    networkConfiguration={"networkMode": "PUBLIC"},  # SANDBOX = no network, PUBLIC = internet access
)
ci_id = ci["codeInterpreterId"]
```

## IAM role for Code Interpreter (S3 access)

```python
import boto3, json
iam = boto3.client("iam")

iam.create_role(
    RoleName="MyCodeInterpreterRole",
    AssumeRolePolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }),
)
iam.put_role_policy(RoleName="MyCodeInterpreterRole", PolicyName="S3Access",
    PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::my-bucket/*"}]}))
```

## Use custom Code Interpreter in Strands agent

```python
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

# Pass custom identifier instead of default
ci_tool = AgentCoreCodeInterpreter(region="us-east-1", identifier="my_ci_id-abc123")

agent = Agent(model=model, tools=[ci_tool.code_interpreter])
```

## Generate presigned URL for S3 chart

```python
s3 = boto3.client("s3")
url = s3.generate_presigned_url("get_object", Params={"Bucket": "my-bucket", "Key": "charts/chart.png"}, ExpiresIn=3600)
```
