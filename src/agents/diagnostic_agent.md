# DiagnosticAgent

Pattern-matching rule engine for incident diagnosis.

## Rules
1. Multiple towers DOWN → FIBER_CUT (confidence: 0.90)
2. Single tower DOWN + power_level = 0 → POWER_OUTAGE (confidence: 0.95)
3. Tower in ALARM → SIGNAL_INTERFERENCE (confidence: 0.85)
4. Default single tower DOWN → POWER_OUTAGE (confidence: 0.80)

## Output
`Incident` object with `root_cause_hypothesis` and `diagnosis_confidence`

**Note**: Tools in tools.py are currently unused. Future work: call tools to gather evidence and dynamically adjust confidence.