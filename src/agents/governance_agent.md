# GovernanceAgent

Reviews remediation plans against company policies and legal requirements.

## Flow
```
(Incident + Plan) → Claude → JSON Parse → GovernanceDecision
```

## Tools Used
- `get_company_policy_document` - Company policies
- Policy research for compliance checks
- Legal/regulatory requirements validation

## Output
`GovernanceDecision` object with:
- `decision` - APPROVE | REJECT_LOW_CONFIDENCE | REJECT_BAD_PLAN | REJECT_POLICY_VIOLATION
- `reason` - Why approved or rejected
- `policies_checked[]` - Which policies were validated
- `legal_requirements_reviewed[]` - Which regulations checked

## Key Features
- Pragmatic: approves reasonable plans, rejects only serious violations
- Provides feedback reason: passed back to diagnostic for plan improvement
- Multi-stakeholder foundation (extensible to security, SLA agents)
