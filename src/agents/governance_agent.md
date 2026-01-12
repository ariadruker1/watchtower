# GovernanceAgent

**Human Role**: Compliance Officer / Legal Reviewer
**Job**: Make sure the remediation plan is safe, legal, and complies with company policies before it goes to a human for approval

## Purpose

Not every action plan is a good idea. Before a human operator approves and executes a plan, this agent acts like a compliance officer who checks: "Does this follow our company policies? Are there any legal/regulatory risks? Is this plan safe?" The goal is to either approve the plan or reject it with specific reasons so it can be improved.

## Flow

```
(Incident + Plan) → Claude → Analyze Policies + Laws → JSON Parse → GovernanceDecision
```

## Tools This Agent Uses

- `get_company_policy_document` - What does our company require?
- Policy research - What regulations apply to telecom incident response?
- Legal research - What are we legally required to do?

## What It Outputs

`GovernanceDecision` object containing:
- `decision` - One of:
  - **APPROVE** - Plan is good to go
  - **REJECT_LOW_CONFIDENCE** - Diagnosis wasn't confident enough
  - **REJECT_BAD_PLAN** - Plan won't work or is risky
  - **REJECT_POLICY_VIOLATION** - Violates company policy or law
- `reason` - Specific explanation of why (used as feedback to improve)
- `policies_checked[]` - Which company policies were reviewed
- `legal_requirements_reviewed[]` - Which regulations were checked

## Key Behaviors

- **Pragmatic, not bureaucratic**: Approves reasonable plans, only rejects serious violations (not overly strict)
- **Feedback provider**: Rejection includes specific reason, not just "no"
- **Policy-aware**: Knows company policies and can access them via tools
- **Legally informed**: Understands telecom regulations and data protection requirements
- **Foundation for expansion**: Can be extended to include separate Security Agent and SLA Agent in future

## When It Gets Called

1. Remediation agent completes the plan
2. Supervisor sends (Incident + Plan) to Governance
3. Governance reviews against policies and legal requirements
4. Returns decision
5. If APPROVE → proceeds to human approval
6. If REJECT → feedback sent back to Diagnostic agent to improve
