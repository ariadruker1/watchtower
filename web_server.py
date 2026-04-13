"""
Web Server: FastAPI backend that wraps the existing simulation engine and multi-agent pipeline,
providing SSE state streaming and control endpoints for the NOC web dashboard.
"""

import asyncio
import json
import random
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from src.simulation.engine import SimulationEngine
from src.agents.supervisor_agent import SupervisorAgent
from src.agent_logger import AgentLogger
from src.data_models import Incident, RemediationPlan, GovernanceDecision


# ---------------------------------------------------------------------------
# Dashboard State  (shared between async web handlers and the sim thread)
# ---------------------------------------------------------------------------

class DashboardState:
    """Thread-safe state bridge between the simulation thread and SSE endpoint."""

    def __init__(self):
        self._lock = threading.Lock()

        # Simulation control
        self.running = False
        self.paused = False
        self.step_through = False  # OFF by default — automatic mode
        self._step_event = threading.Event()
        self._approval_event = threading.Event()
        self._approval_decision: Optional[str] = None

        # Simulation data
        self.tick = 0
        self.telemetry: dict = {}
        self.alerts: list = []
        self.pipeline_phase: str = "idle"
        self.agent_history: list = []
        self.agent_logs: list = []
        self.incident: Optional[Incident] = None
        self.plan: Optional[RemediationPlan] = None
        self.governance: Optional[GovernanceDecision] = None
        self.approval_required = False
        self.tokens_used = 0
        self.token_budget = 5000

        # Change notification
        self._changed = threading.Event()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "tick": self.tick,
                "telemetry": self.telemetry,
                "alerts": [{"tower_id": a.tower_id, "metric": a.metric,
                            "value": a.value, "message": a.message}
                           for a in self.alerts] if self.alerts else [],
                "pipeline_phase": self.pipeline_phase,
                "agent_history": list(self.agent_history),
                "agent_logs": list(self.agent_logs),
                "incident": self.incident.to_dict() if self.incident else None,
                "plan": self.plan.to_dict() if self.plan else None,
                "governance": self.governance.to_dict() if self.governance else None,
                "approval_required": self.approval_required,
                "tokens_used": self.tokens_used,
                "token_budget": self.token_budget,
                "step_through": self.step_through,
                "paused": self.paused,
                "running": self.running,
            }

    def notify(self):
        self._changed.set()

    def wait_for_change(self, timeout: float = 1.0) -> bool:
        result = self._changed.wait(timeout=timeout)
        self._changed.clear()
        return result

    # Step-through helpers
    def wait_for_step(self):
        """Block sim thread until user clicks Next Step (only when step_through is ON).
        Also sets pipeline_phase to 'waiting' and notifies the frontend."""
        if not self.step_through:
            return
        with self._lock:
            self.pipeline_phase = "waiting"
        self._step_event.clear()
        self.notify()
        self._step_event.wait()

    def release_step(self):
        self._step_event.set()

    # Approval helpers
    def wait_for_approval(self) -> str:
        self._approval_event.clear()
        self.approval_required = True
        self.notify()
        self._approval_event.wait()
        self.approval_required = False
        return self._approval_decision

    def submit_approval(self, decision: str):
        self._approval_decision = decision
        self._approval_event.set()


# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

state = DashboardState()
app = FastAPI(title="Watchtower NOC Dashboard")
TOPOLOGY_PATH = Path("config/topology.json")
ANOMALY_TYPES = ["POWER_OUTAGE", "FIBER_CUT", "SIGNAL_INTERFERENCE"]
ANOMALY_PROBABILITY = 0.05


# ---------------------------------------------------------------------------
# Simulation Loop  (runs in a background thread)
# ---------------------------------------------------------------------------

def simulation_loop():
    """Blocking simulation loop — runs in a daemon thread.

    Wrapped in try/finally so state.running is always cleared on exit,
    even if an agent raises an unhandled exception. Without this, a
    crash in (e.g.) the diagnostic agent would leave state.running=True
    and permanently block the frontend from restarting.
    """
    try:
        _simulation_loop_inner()
    except Exception as exc:
        print(f"\n[SimulationLoop] FATAL: unhandled exception: {exc!r}")
        import traceback
        traceback.print_exc()
    finally:
        state.running = False
        state.notify()


def _simulation_loop_inner():
    """Blocking simulation loop — inner implementation."""
    engine = SimulationEngine(topology_file="config/topology.json")
    agent_logger = AgentLogger()
    supervisor = SupervisorAgent(logger=agent_logger, max_budget=state.token_budget)

    # Reuse sub-agents from the supervisor
    monitoring = supervisor.monitoring_agent
    diagnostic = supervisor.diagnostic_agent
    remediation = supervisor.remediation_agent
    governance = supervisor.governance_agent
    llm_client = supervisor.llm_client

    # Confidence boosting state (mirrors supervisor logic)
    incident_counts = defaultdict(int)
    incident_timestamps = defaultdict(float)
    confidence_boost_threshold = 2
    persistence_window = 10

    guaranteed_anomaly_tick = random.randint(5, 15)
    guaranteed_anomaly_injected = False
    tick_counter = 0

    state.running = True
    state.notify()

    while state.running:
        # Pause support
        while state.paused and state.running:
            time.sleep(0.2)
        if not state.running:
            break

        tick_counter += 1
        time.sleep(1)  # 1-second tick interval

        # --- Anomaly injection (same logic as step_through_demo.py) ---
        if not guaranteed_anomaly_injected and tick_counter >= guaranteed_anomaly_tick:
            problem = random.choice(ANOMALY_TYPES)
            engine.inject_anomaly(problem)
            guaranteed_anomaly_injected = True
        elif guaranteed_anomaly_injected and engine.anomaly is None:
            if random.random() < ANOMALY_PROBABILITY:
                problem = random.choice(ANOMALY_TYPES)
                engine.inject_anomaly(problem)

        # --- Tick ---
        telemetry = engine.tick()

        # Update telemetry display (don't clear incident data yet)
        with state._lock:
            state.tick = tick_counter
            state.telemetry = telemetry
        state.notify()

        # --- Stage 1: Monitoring (pure threshold, no LLM) ---
        llm_client.reset_token_count()
        agent_logger.clear_incident_logs()

        alerts = monitoring.analyze_telemetry(telemetry)

        # Build monitoring log entry (monitoring has no LLM, so we create one)
        if alerts:
            monitoring_log = {
                "agent": "MonitoringAgent",
                "natural_language_log": (
                    f"Received: Network telemetry from {len(telemetry)} towers.\n"
                    f"Investigated: Power levels, signal strength, throughput, "
                    f"and tower status against operational thresholds.\n"
                    f"Suggestions: {len(alerts)} alert(s) detected requiring investigation:\n"
                    + "\n".join(f"  - {a.tower_id}: {a.message}" for a in alerts)
                ),
                "tokens": 0,
                "tools": [],
            }
        else:
            monitoring_log = None

        with state._lock:
            state.alerts = alerts
            state.pipeline_phase = "monitoring"
            state.agent_history = ["monitoring"]
            state.agent_logs = [monitoring_log] if monitoring_log else []
            state.incident = None
            state.plan = None
            state.governance = None
            state.approval_required = False
            state.tokens_used = 0
        state.notify()

        if not alerts:
            with state._lock:
                state.pipeline_phase = "idle"
            state.notify()
            continue

        # ===== INCIDENT PROCESSING =====
        # Once alerts are detected, process the full pipeline before next tick.

        # Wait for step (only blocks when step_through is ON)
        state.wait_for_step()

        # --- Stage 2: Diagnostic ---
        with state._lock:
            state.pipeline_phase = "diagnostic"
        state.notify()

        incident = diagnostic.diagnose_alerts(alerts)

        # Confidence boosting (from supervisor_agent.py:86-101)
        if incident:
            incident_key = (incident.incident_type, tuple(sorted(incident.affected_cell_ids)))
            current_time = time.time()
            if (current_time - incident_timestamps.get(incident_key, 0)) < persistence_window:
                incident_counts[incident_key] += 1
            else:
                incident_counts[incident_key] = 1
            incident_timestamps[incident_key] = current_time

            if incident_counts[incident_key] >= confidence_boost_threshold:
                incident.diagnosis_confidence = min(incident.diagnosis_confidence * 1.2, 1.0)

        logs = [monitoring_log] + _format_logs(agent_logger.get_incident_logs())

        with state._lock:
            state.incident = incident
            state.agent_history = ["monitoring", "diagnostic"]
            state.agent_logs = logs
            state.tokens_used = llm_client.total_tokens_used
        state.notify()

        if not incident:
            # Diagnostic failed — log and let the tick loop retry on the next anomaly
            with state._lock:
                state.pipeline_phase = "idle"
            state.notify()
            continue

        state.wait_for_step()

        # --- Stage 3: Remediation ---
        with state._lock:
            state.pipeline_phase = "remediation"
        state.notify()

        plan = remediation.create_plan(incident)
        logs = [monitoring_log] + _format_logs(agent_logger.get_incident_logs())

        with state._lock:
            state.plan = plan
            state.agent_history = ["monitoring", "diagnostic", "remediation"]
            state.agent_logs = logs
            state.tokens_used = llm_client.total_tokens_used
        state.notify()

        if not plan:
            with state._lock:
                state.pipeline_phase = "idle"
            state.notify()
            time.sleep(4)
            continue

        state.wait_for_step()

        # --- Stage 4: Governance ---
        with state._lock:
            state.pipeline_phase = "governance"
        state.notify()

        gov_decision = governance.evaluate(incident, plan)

        # Governance rejection retry (from supervisor_agent.py:124-153)
        if gov_decision.decision != "APPROVE" and llm_client.total_tokens_used < state.token_budget:
            feedback = (f"Governance rejected: {gov_decision.reason}. "
                        f"Need stronger diagnostic evidence and confidence "
                        f"(current: {incident.diagnosis_confidence:.2f}).")
            incident2 = diagnostic.diagnose_alerts(alerts, feedback)
            if incident2 and incident2.diagnosis_confidence > incident.diagnosis_confidence:
                incident = incident2
                plan2 = remediation.create_plan(incident)
                if plan2 and llm_client.total_tokens_used < state.token_budget:
                    plan = plan2
                    gov_decision = governance.evaluate(incident, plan)

        logs = [monitoring_log] + _format_logs(agent_logger.get_incident_logs())

        with state._lock:
            state.incident = incident
            state.plan = plan
            state.governance = gov_decision
            state.agent_history = ["monitoring", "diagnostic", "remediation", "governance"]
            state.agent_logs = logs
            state.tokens_used = llm_client.total_tokens_used
        state.notify()

        state.wait_for_step()

        # --- Stage 5: Human Approval ---
        with state._lock:
            state.pipeline_phase = "approval"
        state.notify()

        decision = state.wait_for_approval()

        if decision == "approve":
            engine.anomaly = None
            engine.anomaly_details = {}

        with state._lock:
            state.pipeline_phase = "idle"
            state.approval_required = False
        state.notify()

    # state.running = False is handled by the simulation_loop wrapper's finally block


def _format_logs(raw_logs: list) -> list:
    """Convert AgentLogger incident logs to JSON-safe dicts for SSE."""
    formatted = []
    for log in raw_logs:
        formatted.append({
            "agent": log.get("agent", ""),
            "natural_language_log": log.get("natural_language_log", ""),
            "tokens": log.get("tokens", 0),
            "tools": log.get("tools_called", []),
        })
    return formatted


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@app.get("/api/topology")
async def get_topology():
    try:
        data = json.loads(TOPOLOGY_PATH.read_text())
        return JSONResponse(content=data)
    except FileNotFoundError:
        return JSONResponse(content=[], status_code=404)


@app.get("/api/events")
async def sse_events():
    async def event_stream():
        while True:
            changed = await asyncio.to_thread(state.wait_for_change, 1.0)
            snap = await asyncio.to_thread(state.snapshot)
            yield f"event: state\ndata: {json.dumps(snap)}\n\n"
            if not state.running and not changed:
                await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no"})


@app.post("/api/start")
async def start_simulation():
    if state.running:
        return JSONResponse(content={"status": "already_running"})
    state.paused = False  # reset any leftover pause from a prior run
    t = threading.Thread(target=simulation_loop, daemon=True)
    t.start()
    return JSONResponse(content={"status": "started"})


@app.post("/api/pause")
async def toggle_pause():
    state.paused = not state.paused
    state.notify()
    return JSONResponse(content={"paused": state.paused})


@app.post("/api/step")
async def advance_step():
    state.release_step()
    return JSONResponse(content={"status": "stepped"})


@app.post("/api/toggle-step-through")
async def toggle_step_through():
    state.step_through = not state.step_through
    # If turning off, release any pending step wait
    if not state.step_through:
        state.release_step()
    state.notify()
    return JSONResponse(content={"step_through": state.step_through})


@app.post("/api/approve")
async def approve_plan():
    state.submit_approval("approve")
    return JSONResponse(content={"status": "approved"})


@app.post("/api/reject")
async def reject_plan():
    state.submit_approval("reject")
    return JSONResponse(content={"status": "rejected"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print(" WATCHTOWER NOC DASHBOARD STARTING")
    print(" URL: http://localhost:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
