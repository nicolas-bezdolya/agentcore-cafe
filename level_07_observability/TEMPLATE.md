# 📋 Level 07 — Templates

## requirements.txt for observability

```
strands-agents[otel]>=1.0.0    # [otel] extra enables OpenTelemetry instrumentation
aws-opentelemetry-distro        # ADOT — auto-instruments Bedrock calls, tool invocations, etc.
```

These two dependencies are all you need. AgentCore Runtime handles the rest automatically.

## Enable Transaction Search (one time per account)

```bash
# 1. Allow X-Ray to write to CloudWatch Logs
aws logs put-resource-policy \
  --policy-name TransactionSearchXRayAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "xray.amazonaws.com"},
      "Action": "logs:PutLogEvents",
      "Resource": [
        "arn:aws:logs:<region>:<account-id>:log-group:aws/spans:*",
        "arn:aws:logs:<region>:<account-id>:log-group:/aws/application-signals/data:*"
      ]
    }]
  }'

# 2. Set trace destination
aws xray update-trace-segment-destination --destination CloudWatchLogs
```

## Enable tracing on Runtime agent (console)

1. Open AgentCore console → Agents runtime
2. Select your agent
3. Tracing pane → Edit → Enable → Save

## View traces

```bash
# Tail runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-id>-DEFAULT --follow

# GenAI Observability Dashboard
# https://console.aws.amazon.com/cloudwatch/home#gen-ai-observability/agent-core
```
