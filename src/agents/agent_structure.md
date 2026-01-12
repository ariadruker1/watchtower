# Watchtower MVP - Agent Architecture

AI-powered incident response with feedback loops and rejection handling.

## Agents

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Monitoring** | Detects anomalies | Telemetry | Alert |
| **Diagnostic** | Root cause analysis | Alert | Incident |
| **Remediation** | Action planning | Incident | RemediationPlan |
| **Governance** | Policy validation | Plan | GovernanceDecision |
| **Supervisor** | Orchestration | All above | Human approval request |

## System Flow

```
Telemetry
    ↓
Monitoring → Diagnostic → Remediation → Governance
                ↑                           ↓
                └─────── Feedback Loop ────┘
                ↓
            Human Approval (y/n)
                ↓
            Reset & Resume
```

## Key Characteristics

- **LLM-Powered**: All agents use Claude AI + tools
- **Feedback Loops**: Rejected plans loop back to diagnostic for improvement
- **Tool Use**: Agents access weather, maintenance, policies, engineer schedules
- **Confidence Scoring**: Each step assigns/updates confidence (0.0-1.0)
- **State Management**: Supervisor maintains mutable incident reference
- **Token Budget**: Enforced max tokens across all agents

## Tools Available

- `get_weather_at_tower` - Local conditions
- `get_tower_maintenance_history` - Recent work
- `lookup_telecom_pattern` - Failure patterns
- `check_regional_news_alerts` - External events
- `get_standard_operating_procedure` - Runbooks
- `get_on_call_engineer_schedule` - Teams available
- `get_company_policy_document` - Policies
