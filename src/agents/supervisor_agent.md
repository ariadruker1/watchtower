# SupervisorAgent

**Human Role**: Operations Director / Incident Commander
**Job**: Oversee the entire incident response process and make sure all agents work together effectively

## Purpose

This is the "boss" agent. Like an operations director during a crisis, the supervisor oversees all other agents, makes sure they do their jobs, handles rejections, and decides when the process is ready for human approval. The supervisor also tracks confidence levels and decides if an incident should be re-analyzed for higher certainty.

## Workflow

```
Telemetry
   ↓
Monitoring → Diagnostic → Remediation → Governance
                ↑                            ↓
                └─ Feedback Loop (if rejected)
                ↓
            Human Approval (y/n)
                ↓
            Reset State
```

## What It Manages

### Agent Orchestration
- Calls agents in sequence (Monitoring → Diagnostic → Remediation → Governance)
- Passes outputs from one agent to the next
- Handles errors if any agent fails

### Rejection Feedback Loop
- Governance rejects → passes rejection reason back to Diagnostic
- Diagnostic re-analyzes with feedback: "Your confidence was too low, find more evidence"
- New plan is created with potentially higher confidence
- Re-evaluated by governance
- Loop continues until: APPROVE or token budget exhausted

### Confidence Boosting
- Tracks same incident type occurring multiple times within 10 seconds
- First occurrence: baseline confidence
- Second occurrence within 10s: boost confidence by 20% (capped at 1.0)
- Rationale: If a problem persists or recurs, we're more confident it's real

### State Management
- Maintains `current_incident` - the Incident object being processed
- Maintains `remediation_plan` - the Plan awaiting human approval
- Maintains `human_approval_required` flag - signals UI to show approval prompt
- Resets all state when human makes a decision (y/n)

### Token Budget Enforcement
- Each incident has a maximum token budget (e.g., 5000 tokens)
- Tracks total tokens used across all agents
- Stops if budget is approaching limit
- Prevents runaway costs

## Key Behaviors

- **Sequential pipeline**: Agents run one after another (not in parallel)
- **Automatic retry with feedback**: If rejected, automatically re-runs diagnostic with feedback
- **Confidence tracking**: Monitors confidence levels at each stage
- **State isolation**: Only supervisor modifies state; agents receive read-only snapshots
- **Token conscious**: Enforces budget limits across entire incident

## When It Gets Called

1. Supervisor.process_telemetry() called by demo/UI
2. Routes telemetry to Monitoring agent
3. If alert detected → routes to Diagnostic
4. Routes diagnosis to Governance
5. If approved → routes to Remediation
6. Routes plan back to Governance for final check
7. If still approved → flags for human approval
8. UI shows approval panel
9. On human decision → resets state and waits for next incident
