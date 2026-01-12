# GovernanceAgent

Single policy check: confidence threshold validation.

## Policy Rule
- **min_confidence_threshold** (from policy.yaml, default 0.8)
- Approve if: `incident.diagnosis_confidence >= threshold`
- Reject if: below threshold

## Output
Boolean pass/fail (no GovernanceDecision object created yet)

**Note**: Only one policy enforced. Future work: expand to multi-rule policy validation with formal GovernanceDecision logging.