# DiagnosticAgent

Investigates network alerts using Claude AI + tools to determine root cause.

## Flow
```
Alert → Claude + Tools → JSON Parse → Incident (with confidence)
```

## Tools Used
- `get_weather_at_tower` - Weather conditions
- `get_tower_maintenance_history` - Recent maintenance
- `lookup_telecom_pattern` - Known failure patterns
- `check_regional_news_alerts` - External events

## Output
`Incident` object with:
- `root_cause_hypothesis` (natural language)
- `diagnosis_confidence` (0.0-1.0)
- `affected_cell_ids` (list)
- `evidence` (supporting data)

## Key Features
- Multi-round tool calling
- Evidence-based confidence scoring
- Feedback loop: accepts rejection reason and re-diagnoses for higher confidence
