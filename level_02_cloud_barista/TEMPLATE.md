# 📋 Level 02 — Templates

## BedrockAgentCoreApp wrapper (minimal)

```python
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

agent = Agent(model=BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0"))

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    """This function is called by AgentCore Runtime for each request."""
    user_input = payload.get("prompt", "")
    response = agent(user_input)
    return response.message["content"][0]["text"]

if __name__ == "__main__":
    app.run()  # Starts HTTP server on port 8080
```

That's it. 4 lines added to your Level 01 agent:
1. `from bedrock_agentcore.runtime import BedrockAgentCoreApp`
2. `app = BedrockAgentCoreApp()`
3. `@app.entrypoint` decorator on your invoke function
4. `app.run()` at the bottom

## AgentCore Starter Toolkit CLI

```bash
# Configure (interactive wizard)
agentcore configure -e agent.py

# Configure (non-interactive, all flags)
agentcore configure \
  -e agent.py \                    # Entrypoint file
  -n my_agent \                    # Agent name (alphanumeric, no dashes)
  -dt direct_code_deploy \         # Deploy type: direct_code_deploy or container
  -rt PYTHON_3_11 \                # Runtime: PYTHON_3_10, PYTHON_3_11, PYTHON_3_12, PYTHON_3_13
  -rf requirements.txt \           # Dependencies file
  --disable-memory \               # Skip memory setup
  --non-interactive                # No prompts

# Deploy to cloud
agentcore deploy

# Invoke
agentcore invoke '{"prompt": "Hello!"}'

# Check status
agentcore status

# View logs
agentcore logs --follow
```

## requirements.txt (minimal for cloud deploy)

```
strands-agents
bedrock-agentcore
boto3
```

## IAM Execution Role (what AgentCore Runtime needs)

The CLI creates this automatically, but here's what it looks like:

Trust Policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {"aws:SourceAccount": "<account-id>"},
      "ArnLike": {"aws:SourceArn": "arn:aws:bedrock-agentcore:<region>:<account-id>:*"}
    }
  }]
}
```

Permissions Policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelInvocation",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:<region>:<account-id>:*"]
    },
    {
      "Sid": "ECRImageAccess",
      "Effect": "Allow",
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      "Resource": ["arn:aws:ecr:<region>:<account-id>:repository/*"]
    },
    {
      "Sid": "ECRTokenAccess",
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams", "logs:DescribeLogGroups"],
      "Resource": ["arn:aws:logs:<region>:<account-id>:log-group:/aws/bedrock-agentcore/runtimes/*"]
    },
    {
      "Sid": "Observability",
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"],
      "Resource": ["*"]
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}
    }
  ]
}
```

Source: [IAM Permissions for AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html) — section "Execution role for running an agent in AgentCore Runtime"
