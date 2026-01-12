# Watchtower MVP - Agent Architecture

Rule-based incident management orchestration.

## Agent Roles

- **`MonitoringAgent`**: Detects metric anomalies via threshold checks
- **`DiagnosticAgent`**: Pattern matching (if-else rules) to determine incident type
- **`RemediationAgent`**: Creates plan from runbooks.yaml
- **`GovernanceAgent`**: Validates confidence >= min_threshold
- **`SupervisorAgent`**: Orchestrates workflow, boosts confidence for persistent issues

## Workflow

```
Telemetry → Monitoring (Alert) → Diagnostic (Incident)
  → Governance (confidence check) → Remediation (Plan)
  → Human Approval (Y/N) → Complete
```

No feedback loops. Linear flow with single governance check at policy threshold.