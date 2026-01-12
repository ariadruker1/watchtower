# Gaps & Improvements

## Critical Issues

### 1. tools.py is Dead Code
- All 6 utility functions unused (weather, maintenance, news, policy, engineer schedule, procedures)
- No imports or calls anywhere in codebase
- **Action**: Delete or refactor as proper Claude tool registry for future LLM integration

### 2. No LLM Integration
- Project claims "AI Self-Healing" but is entirely rule-based
- Agents use hardcoded if-else, no Claude API calls
- tools.py scaffolding suggests intended but incomplete
- **Action**: Implement LLM prompting for diagnostic reasoning (if desired)

### 3. Incomplete Incident Lifecycle
Missing dataclass instantiations:
- `GovernanceDecision` - never created
- `IncidentReport` - never generated
- `ApprovalDecision` - never logged
- `ExecutionResult` - never recorded
- `ImpactSummary` - never instantiated

Workflow missing:
1. Impact assessment phase (IncidentReport)
2. Governance decision logging
3. Operator approval tracking
4. Post-execution result recording

### 4. Path Inconsistencies
| File | Path | Issue |
|------|------|-------|
| remediation_agent.py | `'config/runbooks.yaml'` | Relative, fragile |
| tools.py | `'config/runbooks.yaml'` | Relative, fragile |
| governance_agent.py | `'watchtower_mvp/config/policy.yaml'` | Wrong path |
| simulation/engine.py | `'watchtower_mvp/config/topology.json'` | Relative |
| run_demo.py | `'config/topology.json'` | Relative |

**Action**: Use `pathlib.Path(__file__).parent / 'config'` consistently

## High Priority

### Error Handling
Missing error handling:
- YAML parse errors in governance_agent, remediation_agent
- Config structure validation (missing fields → KeyError)
- Null checks on telemetry_data
- Runbook lookup failures

**Action**: Add try-except, validate configs on load, use `.get()` safely

### Type Hints
- Config attributes not typed: `self.policy: Dict`, `self.runbooks: Dict`
- Good coverage overall (85%)

**Action**: Add missing type hints to config attributes

## Medium Priority

### Code Quality
- Unused import: `time` in diagnostic_agent.py (line 1)
- Missing docstrings:
  - All 5 agent classes (0% coverage)
  - 7 of 15 methods lack docstrings
- Naming inconsistency: `tower_id` vs `cell_id` interchangeable

**Action**:
1. Remove unused import
2. Add class-level docstrings explaining purpose
3. Standardize naming: use `cell_id` throughout

### Unused Helper Function
- `get_affected_cell_ids()` in diagnostic_agent.py defined but only used once
- **Action**: Inline or document if needed for future expansion

### Confidence Boosting
- Ad-hoc logic in SupervisorAgent (20% boost after 2 occurrences in 10s)
- Not policy-driven
- **Action**: Move to configurable policy (if policies expand)

### Truck ID Generation
- Random `TRK-{100-999}` naive
- **Action**: Use more realistic format or proper ID scheme

## Low Priority

### DataModel Issues
- `data_model..py` file exists (typo in filename, probably should be deleted)
- Helper function `get_affected_cell_ids()` could be method
- RemediationAction defined but minimal usage

### Remediation Plan
- `plan_confidence` = `diagnosis_confidence` (no independent assessment)
- **Action**: Validate plan independently

## Optional Future Work

1. **ExecutionAgent** - Execute approved plans (not implemented)
2. **Feedback loops** - No looping back for more info or replanning
3. **Tool integration** - Implement tool calls for evidence gathering
4. **LLM prompting** - Add Claude API for decision making
5. **Audit trail** - Log all decisions (GovernanceDecision, ApprovalDecision)
6. **Multi-checkpoint governance** - More comprehensive policy rules
7. **Rollback strategies** - Multi-step rollback plans
8. **Engineer scheduling** - Actual on-call integration (mocked now)
