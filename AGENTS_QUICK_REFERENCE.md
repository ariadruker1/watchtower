# Agents Quick Reference

## MonitoringAgent (`src/agents/monitoring_agent.py`)
**Input**: telemetry_data dict (tower status, metrics)
**Logic**: Check if `status` == DOWN or ALARM
**Output**: `Alert` object
**Lines**: 44

## DiagnosticAgent (`src/agents/diagnostic_agent.py`)
**Input**: `Alert` list
**Logic**: If-else rules:
- Multiple towers DOWN → FIBER_CUT (0.90)
- Single tower DOWN + power=0 → POWER_OUTAGE (0.95)
- Tower ALARM → SIGNAL_INTERFERENCE (0.85)
- Single tower DOWN → POWER_OUTAGE (0.80)

**Output**: `Incident` object
**Lines**: 67

## GovernanceAgent (`src/agents/governance_agent.md`)
**Input**: `Incident`
**Logic**: `incident.diagnosis_confidence >= policy.min_confidence_threshold`
**Output**: boolean (True = approve, False = reject)
**Lines**: 18
**Config**: policy.yaml (min_confidence_threshold: 0.8)

## RemediationAgent (`src/agents/remediation_agent.py`)
**Input**: `Incident`
**Logic**:
1. Load runbooks.yaml[incident_type]
2. Generate action with random TRK-### ID
3. Set plan_confidence = incident.diagnosis_confidence

**Output**: `RemediationPlan` object
**Lines**: 47

## SupervisorAgent (`src/agents/supervisor_agent.py`)
**Input**: telemetry_data
**Logic**:
1. Monitor → Alert
2. Diagnostic → Incident
3. Governance → pass/fail
4. Remediation → Plan (if approved)
5. Confidence boost (×1.2 if persists >10s, max 1.0)

**Output**: orchestration complete, plan ready
**Lines**: 91

## Data Models (`src/data_models.py`)
**Used**: Alert, Incident, RemediationAction, RemediationPlan
**Unused**: RecommendedAction, GovernanceDecision, IncidentReport, ApprovalDecision, ExecutionResult, ImpactSummary
**Lines**: 284

## Simulation (`src/simulation/engine.py`)
**Input**: scenario selection
**Output**: telemetry dict with injected anomalies
**Scenarios**: POWER_OUTAGE, FIBER_CUT, SIGNAL_INTERFERENCE
**Lines**: 94

## Tools (`src/agents/tools.py`)
**Status**: UNUSED - all 6 functions never called
**Functions**: weather, maintenance_history, news_alerts, procedures, engineer_schedule, policy_doc
**Lines**: 86
