"""
Setup script for Level 09: Creates AgentCore Evaluators (LLM-as-Judge).
Run once: python3.11 setup_evaluations.py
"""

import boto3
import json
import os

REGION = boto3.session.Session().region_name or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
ACCOUNT_ID = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)

print(f"☕ Setting up Evaluations for account {ACCOUNT_ID}...\n")

JUDGE_MODEL = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

evaluators = [
    {"name": "cafe_friendliness", "description": "Is Brew warm and welcoming?", "level": "TRACE",
     "instructions": "You are evaluating a coffee shop AI barista called Brew. Assess how friendly, warm, and welcoming the assistant's response is.\n\nContext: {context}\nAssistant Response: {assistant_turn}",
     "scale": [{"value": 1.0, "label": "Excellent", "definition": "Very warm and enthusiastic"}, {"value": 0.5, "label": "OK", "definition": "Neutral tone"}, {"value": 0.0, "label": "Bad", "definition": "Cold or rude"}]},
    {"name": "cafe_rule_compliance", "description": "Does Brew follow house rules?", "level": "TRACE",
     "instructions": "Check if the barista follows: 1) Max 5 drinks per order 2) Suggest food pairing 3) No competitors 4) Stay professional if rude 5) Confirm price\n\nContext: {context}\nAssistant Response: {assistant_turn}",
     "scale": [{"value": 1.0, "label": "Full Compliance", "definition": "All rules followed"}, {"value": 0.5, "label": "Partial", "definition": "Some rules missed"}, {"value": 0.0, "label": "Non-Compliant", "definition": "Major violation"}]},
]

evaluator_ids = {}
for ev in evaluators:
    config = {"llmAsAJudge": {"modelConfig": {"bedrockEvaluatorModelConfig": {"modelId": JUDGE_MODEL, "inferenceConfig": {"maxTokens": 500, "temperature": 0.0}}},
        "instructions": ev["instructions"], "ratingScale": {"numerical": ev["scale"]}}}
    try:
        resp = agentcore_ctrl.create_evaluator(evaluatorName=ev["name"], description=ev["description"], level=ev["level"], evaluatorConfig=config)
        evaluator_ids[ev["name"]] = resp["evaluatorId"]
        print(f"   ✅ {ev['name']}: {resp['evaluatorId']}")
    except Exception as e:
        if "Conflict" in str(e) or "already exists" in str(e).lower():
            print(f"   ✅ Already exists: {ev['name']}")
        else:
            print(f"   ⚠️ {ev['name']} failed: {e}")
            print(f"   💡 Evaluations may be in preview and not available in {REGION}")

if evaluator_ids:
    ssm.put_parameter(Name="/agentcore-cafe/evaluator_ids", Value=json.dumps(evaluator_ids), Type="String", Overwrite=True)

print(f"\n✅ Evaluations ready! Scores appear in CloudWatch GenAI Dashboard.")


# --- Create Online Evaluation Configuration ---
print(f"\n📊 Creating Online Evaluation Configuration...")
AGENT_ID = None
try:
    # Try to get agent ID from agentcore config
    import yaml
    with open(".bedrock_agentcore.yaml", "r") as f:
        ac_config = yaml.safe_load(f)
    AGENT_ID = ac_config.get("agents", {}).get("agentcore_cafe_barista", {}).get("agent_id", None)
except Exception:
    pass

if not AGENT_ID:
    try:
        agents = agentcore_ctrl.list_agent_runtimes().get("agentRuntimes", [])
        for a in agents:
            if "agentcore_cafe" in a.get("agentRuntimeName", ""):
                AGENT_ID = a["agentRuntimeId"]
                break
    except Exception:
        pass

if not AGENT_ID:
    print("   ⚠️ Could not find agent ID. Set AGENT_ID manually in the script.")
else:
    print(f"   Agent ID: {AGENT_ID}")

try:
    from bedrock_agentcore_starter_toolkit import Evaluation
    eval_client = Evaluation()

    # Collect evaluator IDs (custom + built-in)
    # Get custom evaluator IDs from what we created above
    custom_eval_ids = list(evaluator_ids.values())
    # If we didn't create new ones (they already existed), find them
    if not custom_eval_ids:
        try:
            existing = agentcore_ctrl.list_evaluators()
            for ev in existing.get("evaluators", existing.get("evaluatorSummaries", [])):
                name = ev.get("evaluatorName", ev.get("name", ""))
                if "cafe_" in name:
                    custom_eval_ids.append(ev["evaluatorId"])
        except Exception:
            pass

    all_evaluators = custom_eval_ids + ["Builtin.Helpfulness", "Builtin.GoalSuccessRate", "Builtin.Correctness"]

    config = eval_client.create_online_config(
        config_name="agentcore_cafe_eval_config",
        agent_id=AGENT_ID,
        sampling_rate=100,  # Evaluate 100% of interactions for the workshop
        evaluator_list=all_evaluators,
        config_description="AgentCore Café quality monitoring — friendliness and rule compliance",
        auto_create_execution_role=True,
        enable_on_create=True,
    )
    print(f"   ✅ Online Evaluation Config created: {config.get('onlineEvaluationConfigId', 'OK')}")
except Exception as e:
    print(f"   ⚠️ Online Evaluation Config failed: {e}")
    print(f"   💡 You can create it manually from the AgentCore console → Evaluation → Create evaluation configuration")
    print(f"   💡 Select your agent endpoint and add the evaluators: {list(evaluator_ids.keys())}")
