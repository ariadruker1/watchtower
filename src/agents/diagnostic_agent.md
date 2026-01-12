# DiagnosticAgent

**Human Role**: Field Engineer / Network Troubleshooter
**Job**: Investigate network alerts and determine the root cause of the problem

## Purpose

When something goes wrong in the network, this agent acts like an experienced field engineer who shows up at the tower and investigates. It gathers clues (weather, maintenance history, known failure patterns, recent events) and uses reasoning to figure out what's actually broken. The goal is to give a diagnosis with a confidence score so the team knows how certain we are about what the problem is.

## Flow

```
Alert → Claude + Tools → JSON Parse → Incident (with confidence)
```

## Tools This Agent Uses

- `get_weather_at_tower` - Was it raining/windy? (external factors)
- `get_tower_maintenance_history` - Was work done recently? (human factors)
- `lookup_telecom_pattern` - Does this match known patterns? (pattern library)
- `check_regional_news_alerts` - Are there events in the area? (external context)

## What It Outputs

`Incident` object containing:
- `root_cause_hypothesis` - Plain English explanation of what's broken
- `diagnosis_confidence` - How sure we are (0.0 = wild guess, 1.0 = certain)
- `affected_cell_ids` - Which towers are impacted
- `evidence` - Supporting data that led to this diagnosis

## Key Behaviors

- **Multi-round tool calling**: Can call multiple tools to gather evidence before making a decision
- **Evidence-based confidence**: More and better evidence = higher confidence score
- **Feedback loop**: If governance says "not confident enough," this agent re-diagnoses and tries to find stronger evidence
- **Natural language reasoning**: Uses Claude to think through the problem like a human would

## When It Gets Called

1. Monitoring agent detects an anomaly (metrics out of range)
2. Supervisor sends the alert to Diagnostic
3. Diagnostic gathers tool data and reasons about it
4. Returns Incident object to Supervisor
