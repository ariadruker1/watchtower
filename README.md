# Watchtower MVP

AI-powered incident management demo for telecom network outages using Claude AI.

## Quick Start

```bash
cd watchtower_mvp
pip install -r requirements.txt

# For latest OpenAI-based version:
export OPENAI_API_KEY="your-openai-key"

# For legacy Anthropic-based setups:
export ANTHROPIC_API_KEY="your-anthropic-key"

python step_through_demo.py
```

**Controls**: SPACE=advance, SPACE (approval)=auto-approve, y/n=human decision, l=logs, p=pause, ESC=close logs

## Web Dashboard (NOC UI)

`web_server.py` is a FastAPI backend that exposes the full multi-agent pipeline over HTTP with a live NOC dashboard at `http://localhost:8000`.

### Setup

```bash
pip install fastapi uvicorn python-dotenv
```

Create a `.env` file in `watchtower_mvp/` (or export the variables):

```bash
# .env
OPENAI_API_KEY=your-openai-key        # if using OpenAI
ANTHROPIC_API_KEY=your-anthropic-key  # if using Anthropic
```

### Run

```bash
python web_server.py
# Dashboard → http://localhost:8000
```

Or with uvicorn directly (enables auto-reload during development):

```bash
uvicorn web_server:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves `dashboard.html` |
| `GET` | `/api/topology` | Returns network topology JSON |
| `GET` | `/api/events` | SSE stream of live simulation state |
| `POST` | `/api/start` | Start the simulation loop |
| `POST` | `/api/pause` | Toggle pause/resume |
| `POST` | `/api/step` | Advance one step (step-through mode) |
| `POST` | `/api/toggle-step-through` | Toggle automatic vs. step-through mode |
| `POST` | `/api/approve` | Approve the current remediation plan |
| `POST` | `/api/reject` | Reject the current remediation plan |

### Dashboard Controls

- **Start** — begins the simulation; anomaly injected automatically within the first 5–15 ticks
- **Pause / Resume** — halts the tick loop without losing state
- **Step-Through** — when enabled, each pipeline stage waits for a manual "Next Step" click
- **Approve / Reject** — human-in-the-loop decision on the remediation plan

## How It Works

```
Telemetry → Monitoring → Diagnostic → Remediation → Governance
                             ↑                          ↓
                             └──── Feedback Loop ──────┘
                             ↓
                         Human Approval (y/n)
```

| Agent | Does | Output |
|-------|------|--------|
| **Monitoring** | Detects anomalies | Alert |
| **Diagnostic** | Root cause analysis + tools | Incident (confidence 0.0-1.0) |
| **Remediation** | Creates action plan | RemediationPlan (actions + preventative measures) |
| **Governance** | Validates policy compliance | GovernanceDecision (approve/reject) |
| **Supervisor** | Orchestrates all agents | Feedback loops + confidence boosting |

## Key Features

- **LLM Tool Use**: Agents call tools for weather, maintenance, policies, schedules
- **Feedback Loops**: Rejected plans loop back to diagnostic for improvement
- **Confidence Boosting**: Persistent incidents (+20% confidence, capped at 1.0)
- **Token Tracking**: Enforced per-incident budget
- **3-Stage Logs**: Received → Investigated → Suggestions (natural language)

## Tools Available

- `get_weather_at_tower` | `get_tower_maintenance_history` | `lookup_telecom_pattern`
- `check_regional_news_alerts` | `get_standard_operating_procedure`
- `get_on_call_engineer_schedule` | `get_company_policy_document`

## Configuration

- `config/topology.json` - Network (5 towers)
- `config/telecom_patterns.yaml` - Incident patterns
- `config/runbooks.yaml` - Response procedures

## Anomaly Types

| Type | Effect |
|------|--------|
| **POWER_OUTAGE** | Power level → 10-40% |
| **FIBER_CUT** | Signal + throughput → 20-50% |
| **SIGNAL_INTERFERENCE** | Signal → -130 to -90 dBm |

## Feedback Loop Example

1. Diagnostic: POWER_OUTAGE (confidence 0.75)
2. Governance: ❌ "Confidence < 0.8"
3. Supervisor: Re-run diagnostic with feedback
4. Diagnostic: ✓ Confidence → 0.85 (found more evidence)
5. Remediation: Creates plan
6. Human: y/n approval

## Known Limitations

- ExecutionAgent not implemented (plan approved but not executed in network)
- No persistent audit trail (logs cleared per incident)
- Sequential pipeline (no parallel agent execution)

See `FAQ.md` for detailed technical Q&A.
