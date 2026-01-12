# Watchtower MVP Plan

## Objective
Rule-based incident management demo for telecom network outages with human approval workflow.

## Workflow
Telemetry → Monitoring (detect) → Diagnostics (diagnose) → Governance (policy check) → Remediation (plan) → Human Approval → Complete

## Failure Scenarios
- **Power Outage**: Single tower DOWN, power_level = 0 (confidence: 0.95)
- **Fiber Cut**: Multiple towers DOWN (confidence: 0.90)
- **Signal Interference**: Tower in ALARM state (confidence: 0.85)

## Agents
- **MonitoringAgent**: Threshold-based telemetry filter
- **DiagnosticAgent**: If-else rules to match symptoms → incident type
- **RemediationAgent**: Runbook template filling
- **GovernanceAgent**: Confidence threshold validation (min 0.8)
- **SupervisorAgent**: Orchestrator, confidence boosting (20% boost if incident persists >10s)

## UI
Rich library: live tower status table (left) + agent log (right) + approval prompt (bottom)
