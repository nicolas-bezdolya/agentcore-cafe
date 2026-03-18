# ☕ AgentCore Café — Learn AgentCore one espresso at a time

<p align="center">
  <img src="cover.png" alt="AgentCore Café" width="600">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Strands_Agents-SDK-orange?logo=amazonaws&logoColor=white" alt="Strands Agents">
  <img src="https://img.shields.io/badge/Amazon_Bedrock-AgentCore-purple?logo=amazonaws&logoColor=white" alt="AgentCore">
</p>

> Build a barista AI agent from scratch, adding AgentCore services one level at a time. ☕🚀

---

## 📖 What is this?

A progressive, hands-on repo to learn **Amazon Bedrock AgentCore** through a single fun use case: an AI barista called **Brew** that runs a café.

Each level adds a new AgentCore service. The café gets smarter, the code stays simple.

Each level folder (`level_XX_name/`) contains:
- `INSTRUCTIONS.md` — Step-by-step guide to complete the level
- `TEMPLATE.md` — Copy-paste code snippets and patterns for reference
- `agent.py` — The agent code for that level (copy to root to use)
- `setup_*.py` — Setup scripts for AWS resources (when needed)
- `comic.png` — A comic strip summarizing what Brew learned

---

## 🏗️ Levels

| # | Level | AgentCore Service | What Brew learns |
|---|-------|-------------------|-----------------|
| 01 | **Local Barista** | Strands Agent (local) | Take orders, recommend drinks |
| 02 | **Cloud Barista** | Runtime (deploy) | Run in the cloud, invoke remotely |
| 03 | **Barista with Memory** | Memory (STM + LTM) | Remember your favorite order across sessions |
| 04 | **Supply Chain** | Gateway + Lambda | Check stock, process orders via MCP tools |
| 05 | **Staff vs Customers** | Identity (Inbound Auth) | Authenticate users with JWT, role-based access |
| 06 | **Daily Report** | Code Interpreter | Generate sales charts with S3 download |
| 07 | **Café Dashboard** | Observability (ADOT) | Trace orders, monitor latency, CloudWatch dashboards |
| 08 | **House Rules** | Policy (Cedar) | Enforce identity-based rules on Gateway tools |
| 09 | **Quality Control** | Evaluations (LLM-as-Judge) | Monitor response quality continuously |

---

## ⚙️ Prerequisites

- Python 3.11+
- AWS account with Bedrock access (Level 02+)
- AWS CLI configured

### Install dependencies

```bash
python3.11 -m pip install bedrock-agentcore-starter-toolkit strands-agents strands-agents-tools boto3
```

### AWS Credentials Setup

Configure a named profile with your credentials:
```bash
aws configure --profile <your-profile>
```

Or if you have temporary credentials (workshop, SSO, etc.):
```bash
aws configure set aws_access_key_id <your-key> --profile <your-profile>
aws configure set aws_secret_access_key <your-secret> --profile <your-profile>
aws configure set aws_session_token <your-token> --profile <your-profile>
aws configure set region <your-region> --profile <your-profile>
```

Then before running any level:
```bash
export AWS_PROFILE=<your-profile>
```

---

## ⚡ Get Started

Head to [Level 01](level_01_local_barista/INSTRUCTIONS.md) and follow the instructions. No AWS account needed for the first level.

---

## 🧹 Cleanup

When you're done with the workshop, delete all resources to avoid ongoing charges:

```bash
python3.11 cleanup.py
```

This deletes: DynamoDB tables, Lambda functions, Gateway, Cognito pools, Memory, Code Interpreter, S3 bucket, Policy Engine, Evaluators, IAM roles, and the AgentCore Runtime agent.

---

## 🎁 Extras

Ready-to-use templates for extending Brew with more AgentCore capabilities:

| Extra | What it does |
|---|---|
| 🌊 Streaming | Brew responds token by token via WebSocket |
| 🌐 Browser Tool | Brew navigates the web for recipes and supplier info |
| 🧠 Episodic Memory | Additional LTM strategy — Brew learns patterns from experience |
| 🤖 Multi-Agent | Split Brew into specialized agents (orders, inventory, reports) |
| 🔗 A2A Protocol | Expose Brew as an A2A server for cross-agent communication |
| 📡 MCP Server | Expose Brew as an MCP server for tool discovery |
| 🔒 VPC Networking | Run Brew inside your VPC for private resource access |
| 🔑 Outbound Auth | Brew accesses Google Calendar, GitHub, Slack on behalf of users |
| 🛡️ Bedrock Guardrails | Content filtering — block harmful content, denied topics, PII |
| 📊 Structured Output | Get typed Pydantic responses from Brew |

➡️ [See all extras](EXTRAS.md)

---

## 👤 Author

Nicolás Bezdolya

---

> _"First, we brew. Then, we scale."_ ☕
