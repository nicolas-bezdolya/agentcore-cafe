"""
AgentCore Café — Level 03: Setup Long-Term Memory for Brew ☕🧠
Creates LTM with extraction strategies and adds memory permissions to the runtime execution role.
Run this locally after testing STM to upgrade Brew's memory.
"""

import json
import boto3
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
    SemanticStrategy,
    UserPreferenceStrategy,
)

region = boto3.session.Session().region_name or "us-west-2"
account_id = boto3.client("sts").get_caller_identity()["Account"]
iam = boto3.client("iam")

# --- Step 1: Create LTM ---
print("☕ Creating Long-Term Memory for Brew...\n")

memory_manager = MemoryManager(region_name=region)

memory = memory_manager.get_or_create_memory(
    name="AgentCoreCafe_LTM",
    description="Long-term memory for AgentCore Café barista",
    strategies=[
        UserPreferenceStrategy(
            name="coffee_prefs",
            description="Captures coffee preferences like milk type, strength, etc.",
            namespaces=["cafe/customer/{actorId}/preferences/"],
        ),
        SemanticStrategy(
            name="customer_facts",
            description="Stores facts like name, dietary restrictions, etc.",
            namespaces=["cafe/customer/{actorId}/facts/"],
        ),
    ],
    event_expiry_days=30,
)

memory_id = memory.id
memory_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{memory_id}"
print(f"✅ LTM Memory ID: {memory_id}\n")

# --- Step 2: Add memory permissions to the runtime execution role ---
print("🔐 Adding memory permissions to runtime execution role...")

# Find the runtime execution role that the agent is actually using
try:
    agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name=region)
    agents = agentcore_ctrl.list_agent_runtimes().get("agentRuntimes", [])
    runtime_role = None
    for a in agents:
        if "agentcore_cafe" in a.get("agentRuntimeName", ""):
            detail = agentcore_ctrl.get_agent_runtime(agentRuntimeId=a["agentRuntimeId"])
            role_arn = detail.get("roleArn", detail.get("executionRoleArn", ""))
            if role_arn:
                runtime_role = role_arn.split("/")[-1]
                break

    # Fallback: search IAM roles
    if not runtime_role:
        for role in iam.list_roles()["Roles"]:
            if role["RoleName"].startswith("AmazonBedrockAgentCoreSDKRuntime"):
                runtime_role = role["RoleName"]
                break

    if runtime_role:
        memory_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:DeleteEvent",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:GetMemoryRecord",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:ListMemories",
                ],
                "Resource": "*",
            }],
        }
        iam.put_role_policy(
            RoleName=runtime_role,
            PolicyName="AgentCoreMemoryAccess",
            PolicyDocument=json.dumps(memory_policy),
        )
        print(f"✅ Added memory permissions to {runtime_role}")
    else:
        print("⚠️ Runtime execution role not found. Deploy the agent first, then re-run this script.")
except Exception as e:
    print(f"⚠️ Could not add permissions: {e}")
    print("   You may need to add them manually (see INSTRUCTIONS.md troubleshooting)")

# --- Summary ---
print(f"\n{'=' * 60}")
print("To upgrade to LTM:")
print(f"  1. In agent.py, set: MEMORY_ID = \"{memory_id}\"")
print(f"  2. In .bedrock_agentcore.yaml, update:")
print(f"     mode: STM_AND_LTM")
print(f"     memory_id: {memory_id}")
print(f"     memory_arn: {memory_arn}")
print(f"  3. Run: agentcore deploy")
print(f"  4. Wait 60 seconds after first message for LTM extraction")
print(f"{'=' * 60}")
