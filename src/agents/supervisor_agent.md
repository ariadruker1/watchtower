# SupervisorAgent

Workflow orchestrator with confidence boosting.

## Process
1. Route telemetry to MonitoringAgent
2. If alert: route to DiagnosticAgent → create Incident
3. Route Incident to GovernanceAgent for confidence check
4. If approved: route to RemediationAgent → create Plan
5. Flag for human approval

## Confidence Boosting
- Track persistent incidents (same type within 10 seconds)
- On second occurrence: multiply confidence by 1.2 (max 1.0)
- Helps overcome governance threshold for repeat issues

## Output
Orchestration complete; RemediationPlan ready for operator approval
