"""
☕ AgentCore Café — Cleanup
Deletes ALL resources created by the workshop to avoid ongoing charges.
Run this when you're done with all levels.
"""

import boto3
import json
import time
import subprocess

region = boto3.session.Session().region_name or "us-west-2"
account_id = boto3.client("sts").get_caller_identity()["Account"]
iam = boto3.client("iam")
agentcore_ctrl = boto3.client("bedrock-agentcore-control", region_name=region)

print(f"☕ Cleaning up AgentCore Café resources (account {account_id}, region {region})...\n")

# --- Online Evaluation Configs (Level 09) — must delete BEFORE evaluators ---
print("🗑️ Online Evaluation Configs...")
try:
    configs = agentcore_ctrl.list_online_evaluation_configs().get("onlineEvaluationConfigs", [])
    for c in configs:
        if "agentcore_cafe" in c.get("onlineEvaluationConfigName", ""):
            agentcore_ctrl.delete_online_evaluation_config(onlineEvaluationConfigId=c["onlineEvaluationConfigId"])
            print(f"   ✅ Deleted: {c['onlineEvaluationConfigName']}")
            time.sleep(2)
except Exception as e:
    print(f"   ⚠️ {e}")

# --- Evaluators (Level 09) ---
print("🗑️ Evaluators...")
try:
    resp = agentcore_ctrl.list_evaluators()
    evaluators = resp.get("evaluators", resp.get("evaluatorSummaries", []))
    for ev in evaluators:
        name = ev.get("evaluatorName", ev.get("name", ""))
        if "cafe_" in name:
            agentcore_ctrl.delete_evaluator(evaluatorId=ev["evaluatorId"])
            print(f"   ✅ Deleted: {name}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- Policy Engine (Level 08) — detach from gateway first ---
print("🗑️ Policy Engine...")
try:
    engines = agentcore_ctrl.list_policy_engines().get("policyEngines", [])
    for eng in engines:
        if "agentcore_cafe" in eng.get("name", ""):
            eid = eng["policyEngineId"]
            # Delete all policies first
            while True:
                try:
                    policies = agentcore_ctrl.list_policies(policyEngineId=eid).get("policies", [])
                    if not policies:
                        break
                    for pol in policies:
                        agentcore_ctrl.delete_policy(policyEngineId=eid, policyId=pol["policyId"])
                        print(f"      Deleted policy: {pol.get('name', pol['policyId'])}")
                except Exception:
                    break
            time.sleep(2)
            agentcore_ctrl.delete_policy_engine(policyEngineId=eid)
            print(f"   ✅ Deleted engine: {eid}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- AgentCore Gateway (Level 04) — delete targets first, then gateway ---
print("🗑️ Gateway...")
try:
    gateways = agentcore_ctrl.list_gateways().get("items", [])
    for g in gateways:
        name = g.get("name", "")
        if "agentcore-cafe" in name.lower() or "agentcore_cafe" in name.lower():
            gid = g["gatewayId"]
            # Delete targets first
            targets = agentcore_ctrl.list_gateway_targets(gatewayIdentifier=gid).get("items", [])
            for t in targets:
                agentcore_ctrl.delete_gateway_target(gatewayIdentifier=gid, targetIdentifier=t["targetId"])
                print(f"      Deleted target: {t.get('name', t['targetId'])}")
            time.sleep(2)
            agentcore_ctrl.delete_gateway(gatewayIdentifier=gid)
            print(f"   ✅ Deleted gateway: {name}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- Custom Code Interpreters (Level 06) ---
print("🗑️ Code Interpreters...")
try:
    ci_list = agentcore_ctrl.list_code_interpreters().get("codeInterpreterSummaries", [])
    dp = boto3.client("bedrock-agentcore", region_name=region)
    for ci in ci_list:
        if "agentcore_cafe" in ci.get("name", ""):
            ci_id = ci["codeInterpreterId"]
            # Stop active sessions
            try:
                sessions = dp.list_code_interpreter_sessions(codeInterpreterIdentifier=ci_id).get("items", [])
                for sess in sessions:
                    if sess.get("status") == "READY":
                        dp.stop_code_interpreter_session(codeInterpreterIdentifier=ci_id, sessionId=sess["sessionId"])
                        print(f"      Stopped session: {sess['sessionId']}")
                time.sleep(2)
            except Exception:
                pass
            agentcore_ctrl.delete_code_interpreter(codeInterpreterId=ci_id)
            print(f"   ✅ Deleted: {ci_id}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- AgentCore Memory (Level 03) ---
print("🗑️ Memory...")
try:
    memories = agentcore_ctrl.list_memories().get("memories", [])
    for m in memories:
        mid = m.get("id", m.get("memoryId", ""))
        mname = m.get("name", "")
        if "agentcorecafe" in mname.lower().replace("_", "").replace("-", "") or mname == "AgentCoreCafe_Memory":
            agentcore_ctrl.delete_memory(memoryId=mid)
            print(f"   ✅ Deleted: {mname}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- S3 Buckets (Level 06 charts + deploy bucket) ---
print("🗑️ S3 Buckets...")
s3r = boto3.resource("s3", region_name=region)
for bucket_name in [f"agentcore-cafe-charts-{account_id}", f"bedrock-agentcore-codebuild-sources-{account_id}-{region}"]:
    try:
        bucket = s3r.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.delete()
        print(f"   ✅ Deleted: {bucket_name}")
    except Exception as e:
        if "NoSuchBucket" in str(e) or "not found" in str(e).lower():
            pass
        else:
            print(f"   ⚠️ {bucket_name}: {e}")

# --- DynamoDB Tables (Level 04) ---
print("🗑️ DynamoDB Tables...")
ddb = boto3.client("dynamodb", region_name=region)
for table in ["agentcore-cafe-inventory", "agentcore-cafe-orders"]:
    try:
        ddb.delete_table(TableName=table)
        print(f"   ✅ Deleted: {table}")
    except Exception:
        pass

# --- Lambda Functions (Level 04) ---
print("🗑️ Lambda Functions...")
lam = boto3.client("lambda", region_name=region)
for fn in ["agentcore-cafe-check-stock", "agentcore-cafe-place-order"]:
    try:
        lam.delete_function(FunctionName=fn)
        print(f"   ✅ Deleted: {fn}")
    except Exception:
        pass

# --- Cognito User Pools (Level 04 gateway + Level 05 identity) ---
print("🗑️ Cognito User Pools...")
cog = boto3.client("cognito-idp", region_name=region)
try:
    for pool in cog.list_user_pools(MaxResults=20)["UserPools"]:
        name = pool.get("Name", "")
        if "agentcorecafe" in name.lower().replace("-", "").replace("_", "") or "agentcore-gateway" in name.lower():
            desc = cog.describe_user_pool(UserPoolId=pool["Id"])["UserPool"]
            domain = desc.get("Domain")
            if domain:
                cog.delete_user_pool_domain(UserPoolId=pool["Id"], Domain=domain)
            cog.delete_user_pool(UserPoolId=pool["Id"])
            print(f"   ✅ Deleted: {name}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- SSM Parameters ---
print("🗑️ SSM Parameters...")
ssm = boto3.client("ssm", region_name=region)
ssm_keys = [
    "lambda_role_arn", "check_stock_lambda_arn", "place_order_lambda_arn",
    "gateway_url", "gateway_client_id", "gateway_client_secret",
    "gateway_token_endpoint", "gateway_scope",
    "cognito_pool_id", "cognito_client_id", "cognito_discovery_url",
    "stm_memory_id", "ltm_memory_id",
    "charts_bucket", "charts_ci_id",
    "policy_engine_id", "policy_engine_arn",
    "evaluator_ids",
]
for key in ssm_keys:
    try:
        ssm.delete_parameter(Name=f"/agentcore-cafe/{key}")
        print(f"   ✅ /agentcore-cafe/{key}")
    except Exception:
        pass

# --- IAM Roles ---
print("🗑️ IAM Roles...")
for role_name in ["AgentCoreCafe-LambdaRole", "AmazonBedrockAgentCoreCafeCharts"]:
    try:
        for p in iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=p["PolicyArn"])
        for p in iam.list_role_policies(RoleName=role_name)["PolicyNames"]:
            iam.delete_role_policy(RoleName=role_name, PolicyName=p)
        iam.delete_role(RoleName=role_name)
        print(f"   ✅ Deleted: {role_name}")
    except Exception:
        pass

# Evaluation execution role
try:
    for page in iam.get_paginator("list_roles").paginate():
        for role in page["Roles"]:
            if role["RoleName"].startswith("AgentCoreEvalsSDK-"):
                for p in iam.list_role_policies(RoleName=role["RoleName"])["PolicyNames"]:
                    iam.delete_role_policy(RoleName=role["RoleName"], PolicyName=p)
                iam.delete_role(RoleName=role["RoleName"])
                print(f"   ✅ Deleted: {role['RoleName']}")
                break
        else:
            continue
        break
except Exception:
    pass

# Remove extra policies from Runtime role
try:
    for page in iam.get_paginator("list_roles").paginate():
        for role in page["Roles"]:
            if role["RoleName"].startswith("AmazonBedrockAgentCoreSDKRuntime-"):
                for policy_name in ["CodeInterpreterCustomAndS3", "CognitoAccess", "DynamoDBAccess", "SSMReadAccess"]:
                    try:
                        iam.delete_role_policy(RoleName=role["RoleName"], PolicyName=policy_name)
                        print(f"   ✅ Removed {policy_name} from {role['RoleName']}")
                    except Exception:
                        pass
                break
        else:
            continue
        break
except Exception:
    pass

# --- CloudWatch Log Groups ---
print("🗑️ CloudWatch Log Groups...")
logs = boto3.client("logs", region_name=region)
try:
    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate(logGroupNamePrefix="/aws/bedrock-agentcore/"):
        for lg in page["logGroups"]:
            if "agentcore_cafe" in lg["logGroupName"] or "cafe_barista" in lg["logGroupName"]:
                logs.delete_log_group(logGroupName=lg["logGroupName"])
                print(f"   ✅ Deleted: {lg['logGroupName']}")
    # Evaluation results log groups
    for page in paginator.paginate(logGroupNamePrefix="/aws/bedrock-agentcore/evaluations/"):
        for lg in page["logGroups"]:
            if "agentcore_cafe" in lg["logGroupName"]:
                logs.delete_log_group(logGroupName=lg["logGroupName"])
                print(f"   ✅ Deleted: {lg['logGroupName']}")
except Exception as e:
    print(f"   ⚠️ {e}")

# --- AgentCore Runtime (delete deployed agent) ---
print("\n🗑️ Destroying AgentCore Runtime agent...")
try:
    result = subprocess.run(
        ["agentcore", "destroy", "--agent", "agentcore_cafe_barista", "--force", "--delete-ecr-repo"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        print("   ✅ AgentCore Runtime agent destroyed")
    else:
        print(f"   ⚠️ {result.stderr.strip()[:200]}")
        print("   Run manually: agentcore destroy --agent agentcore_cafe_barista --force --delete-ecr-repo")
except FileNotFoundError:
    print("   ⚠️ agentcore CLI not found")
except Exception as e:
    print(f"   ⚠️ {e}")

print("\n✅ Cleanup complete! All AgentCore Café resources have been removed.")
