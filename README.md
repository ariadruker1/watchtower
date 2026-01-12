# Watchtower MVP

AI-powered incident management demo for telecom network outages using OpenAI GPT-3.5-turbo.

## Setup

```bash
cd watchtower_mvp
pip install -r requirements.txt
export OPENAI_API_KEY="your-openai-api-key-here"
python run_demo.py
```

**Cost**: ~$0.0005 per incident with GPT-3.5-turbo (~20K incidents per $10)

**Controls**: Press 'p' to pause, Ctrl+C to exit, 'Y/N' for approval prompts.

## Architecture

5 LLM-powered agents orchestrate incident response with token budgeting (1500 tokens/incident):

```
Telemetry → Monitoring → Diagnostic (400 tokens) → Governance (250 tokens)
  → Remediation (400 tokens) → Human Approval
```

### MonitoringAgent
- Detects metric anomalies via threshold checks
- Returns `Alert` objects

### DiagnosticAgent (OpenAI + Tool Use)
- Uses tools: weather, maintenance history, news alerts, telecom pattern KB
- Claude-like persona: "veteran field engineer"
- Returns `Incident` with confidence score (0.0-1.0)
- Feedback loop: Can re-diagnose with evidence if rejected by governance

### GovernanceAgent (OpenAI + Tool Use)
- Policy compliance validation (min confidence 0.8)
- Returns `GovernanceDecision` with reason code
- Can reject for: low confidence, bad plan, policy violations

### RemediationAgent (OpenAI + Tool Use)
- Multi-step action planning from runbooks
- Consults engineer availability
- Returns `RemediationPlan` with rollback strategy

### SupervisorAgent
- Orchestrates multi-agent workflow
- Enforces token budget (stops if approaching 1500 tokens)
- Implements feedback loops (max 1 retry per rejection)
- Confidence boosting: +20% on persistent incidents (within 10s)
- Displays token usage in UI header

## LLM Features

- **Model**: GPT-3.5-turbo (cost-optimized)
- **Tool Use**: Autonomous function calling for agents
- **Token Tracking**: Per-agent and per-incident budgets
- **Logging**: All prompts, responses, tool calls logged to memory + UI
- **Feedback Loops**: Agents can request more analysis before governance approval

## Configuration Files

- `config/policy.yaml` - Policy thresholds (min_confidence: 0.8)
- `config/runbooks.yaml` - Incident response procedures
- `config/topology.json` - 5-tower NYC network
- `config/telecom_patterns.yaml` - Knowledge base of failure patterns

## UI Display

- **Header**: Token usage counter, pause status
- **Left Panel**: Live tower status table (OK/ALARM/DOWN)
- **Right Panel**: LLM agent activity log (agent names, token usage, tools called)
- **Footer**: Human approval prompt (on demand)

## Feedback Loop Example

1. DiagnosticAgent diagnoses POWER_OUTAGE (confidence: 0.75)
2. GovernanceAgent rejects: "Confidence 0.75 < threshold 0.8"
3. SupervisorAgent asks Diagnostic to re-analyze with feedback
4. Diagnostic uses more tools, boosts confidence to 0.82
5. GovernanceAgent approves
6. RemediationAgent creates plan
7. Human operator approves/rejects

## Known Limitations

- ExecutionAgent not implemented (plan is approved but not executed)
- No post-execution impact tracking
- No persistent audit trail (logs cleared per incident)

See `PLAN.md` and `GAPS_AND_IMPROVEMENTS.md` for full roadmap.
