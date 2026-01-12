# RemediationAgent

**Human Role**: Operations Manager / Action Planner
**Job**: Create a detailed action plan to fix the problem and prevent it from happening again

## Purpose

Once we know what's broken, someone needs to create a step-by-step plan to fix it. This agent acts like an operations manager who knows the playbooks (runbooks), has access to available teams, and can create a realistic action plan. The goal is to generate actions that can be executed immediately, plus preventative measures that stop the problem from recurring.

## Flow

```
Incident → Claude + Runbooks + Tools → JSON Parse → RemediationPlan
```

## Tools This Agent Uses

- `get_standard_operating_procedure` - What's the official playbook for this incident type?
- `get_on_call_engineer_schedule` - Who's available? (Response Team Alpha/Beta, Service Unit Charlie)

## What It Outputs

`RemediationPlan` object containing:
- `actions[]` - Immediate steps to fix it (e.g., "Dispatch V001 to T001", "Restart power unit")
- `future_preventative_measures[]` - Long-term fixes (e.g., "Install redundant power supply", "Upgrade fiber monitoring")
- `verification_steps[]` - How we confirm the fix worked (e.g., "Check power level at T001")
- `plan_confidence` - How likely this plan will work (0.0-1.0)
- `risk_assessment` - What could go wrong if we execute this

## Key Behaviors

- **Runbook-informed**: Uses official company playbooks as a basis, not making things up
- **Team-aware**: Knows which teams are available and their ETA
- **Vehicle naming**: Uses V### format (V001, V002) for dispatch units, not T### which confuses with tower IDs
- **Preventative mindset**: Doesn't just fix the immediate problem, also suggests how to prevent it next time
- **Feedback acceptance**: If governance rejects the plan, accepts feedback and re-plans

## When It Gets Called

1. Diagnostic agent completes diagnosis
2. Supervisor sends Incident to Remediation
3. Remediation consults runbooks and engineer availability
4. Creates detailed plan
5. Returns RemediationPlan to Supervisor
