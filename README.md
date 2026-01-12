# Watchtower MVP

AI-powered incident management demo for telecom network outages using Claude AI.

## Quick Start

```bash
cd watchtower_mvp
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
python step_through_demo.py
```

**Controls**: SPACE=advance, SPACE (approval)=auto-approve, y/n=human decision, l=logs, p=pause, ESC=close logs

## How It Works

```
Telemetry → Monitoring → Diagnostic → Remediation → Governance
                             ↑                          ↓
                             └──── Feedback Loop ──────┘
                             ↓
                         Human Approval (y/n)
```

| Agent | Does | Output |
|-------|------|--------|
| **Monitoring** | Detects anomalies | Alert |
| **Diagnostic** | Root cause analysis + tools | Incident (confidence 0.0-1.0) |
| **Remediation** | Creates action plan | RemediationPlan (actions + preventative measures) |
| **Governance** | Validates policy compliance | GovernanceDecision (approve/reject) |
| **Supervisor** | Orchestrates all agents | Feedback loops + confidence boosting |

## Key Features

- **LLM Tool Use**: Agents call tools for weather, maintenance, policies, schedules
- **Feedback Loops**: Rejected plans loop back to diagnostic for improvement
- **Confidence Boosting**: Persistent incidents (+20% confidence, capped at 1.0)
- **Token Tracking**: Enforced per-incident budget
- **3-Stage Logs**: Received → Investigated → Suggestions (natural language)

## Tools Available

- `get_weather_at_tower` | `get_tower_maintenance_history` | `lookup_telecom_pattern`
- `check_regional_news_alerts` | `get_standard_operating_procedure`
- `get_on_call_engineer_schedule` | `get_company_policy_document`

## Configuration

- `config/topology.json` - Network (5 towers)
- `config/telecom_patterns.yaml` - Incident patterns
- `config/runbooks.yaml` - Response procedures

## Anomaly Types

| Type | Effect |
|------|--------|
| **POWER_OUTAGE** | Power level → 10-40% |
| **FIBER_CUT** | Signal + throughput → 20-50% |
| **SIGNAL_INTERFERENCE** | Signal → -130 to -90 dBm |

## Feedback Loop Example

1. Diagnostic: POWER_OUTAGE (confidence 0.75)
2. Governance: ❌ "Confidence < 0.8"
3. Supervisor: Re-run diagnostic with feedback
4. Diagnostic: ✓ Confidence → 0.85 (found more evidence)
5. Remediation: Creates plan
6. Human: y/n approval

## Known Limitations

- ExecutionAgent not implemented (plan approved but not executed in network)
- No persistent audit trail (logs cleared per incident)
- Sequential pipeline (no parallel agent execution)

See `FAQ.md` for detailed technical Q&A.
