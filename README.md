# Watchtower MVP

Rule-based incident management demo for telecom network outages.

## Running

```bash
cd watchtower_mvp
pip install -r requirements.txt
python run_demo.py
```

Controls: Press 'p' to pause, Ctrl+C to exit, 'Y/N' for approval prompts.

## Architecture

5 agents orchestrate a linear workflow:

```
Telemetry → Monitoring → Diagnostic → Governance → Remediation → Approval
```

### MonitoringAgent
- Detects metric anomalies (power, signal, throughput)
- Returns `Alert`

### DiagnosticAgent
- Pattern matching (if-else rules)
- Maps symptoms → incident type + confidence
- Returns `Incident`

### GovernanceAgent
- Validates confidence >= `min_confidence_threshold` (0.8)
- Returns boolean pass/fail

### RemediationAgent
- Looks up runbook by incident type
- Fills template with random truck ID
- Returns `RemediationPlan`

### SupervisorAgent
- Orchestrates workflow
- Boosts confidence 20% on persistent incidents (same type within 10s)
- Interfaces with human operator

## Current Gaps

1. **No LLM integration** - All agents are purely rule-based
2. **tools.py is unused** - 6 helper functions defined but never called
3. **Incomplete workflow** - Missing:
   - `IncidentReport` generation (impact assessment)
   - `GovernanceDecision` logging
   - `ApprovalDecision` tracking
   - `ExecutionResult` recording
   - Multi-checkpoint governance
4. **ExecutionAgent** - Not implemented; human approves but plan doesn't execute
5. **Path inconsistencies** - Config paths hardcoded/relative, fragile
6. **Error handling** - Minimal; no YAML validation or null checks

## Next Steps (Code Phase)

1. Fix path handling (use `pathlib`)
2. Add error handling & config validation
3. Remove unused `tools.py` or refactor as Claude tool registry
4. Implement `IncidentReport` generation
5. Add LLM prompting to agents (if intended)
6. Complete incident lifecycle tracking
7. Implement ExecutionAgent
8. Add docstrings & type hints

See `PLAN.md` and agent docs in `src/agents/` for details.
