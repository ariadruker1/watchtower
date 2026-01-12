# SupervisorAgent

Orchestrates all agents in sequence with rejection feedback loops.

## Workflow
```
Telemetry
   ↓
Monitoring → Diagnostic → Remediation → Governance
                ↑                            ↓
                └─ Feedback Loop (if rejected)
                ↓
            Human Approval
                ↓
            Reset State
```

## Rejection Loop
- Governance rejects → passes reason back to Diagnostic
- Diagnostic re-analyzes with feedback: aims for higher confidence
- New plan created + re-evaluated
- Loop until: APPROVE or token budget exhausted

## Confidence Boosting
- Same incident type within 10s window → boost confidence 20% (max 1.0)
- Persistence indicates higher certainty

## State Management
- `current_incident` - Mutable reference to Incident
- `remediation_plan` - Plan object for approval
- `human_approval_required` - Flag for UI display
- Reset on user decision (y/n)

## Key Features
- Sequential pipeline (no parallelization)
- Automatic retry with feedback
- Token budget enforcement
- Incident deduplication via persistence tracking
