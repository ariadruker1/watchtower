# RemediationAgent

Creates detailed action plans using Claude AI + runbooks + engineer availability.

## Flow
```
Incident → Claude + Tools → JSON Parse → RemediationPlan
```

## Tools Used
- `get_standard_operating_procedure` - Runbook for incident type
- `get_on_call_engineer_schedule` - Available teams (Response Team Alpha/Beta, Service Unit Charlie)

## Output
`RemediationPlan` object with:
- `actions[]` - Immediate remediation steps (V### format vehicles)
- `future_preventative_measures[]` - Long-term prevention
- `verification_steps[]` - How to confirm fix worked
- `plan_confidence` - Likelihood of success (0.0-1.0)
- `risk_assessment` - Risk level summary

## Key Features
- Vehicle IDs use V### format (V001, V002, etc.)
- Natural language actions (concise and actionable)
- Accepts feedback: re-plans if governance rejects
