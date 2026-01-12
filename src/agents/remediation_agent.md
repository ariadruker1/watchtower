# RemediationAgent

Template-based plan generation from runbooks.

## Process
1. Load runbooks.yaml by incident_type
2. Generate action description with random truck ID (TRK-###)
3. Create RemediationPlan with `plan_confidence = incident.diagnosis_confidence`

## Output
`RemediationPlan` with single action and minimal rollback

**Note**: plan_confidence directly copies diagnosis_confidence. Future work: independent plan validation, multi-step rollback strategies, engineer availability checking.