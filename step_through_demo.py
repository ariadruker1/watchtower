#!/usr/bin/env python3
"""Step-through demo showing detailed agent processing when anomalies occur."""

import time
import random
import sys
import select
import tty
import termios
import json
from collections import deque
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm
from typing import Optional

from src.simulation.engine import SimulationEngine
from src.agents.supervisor_agent import SupervisorAgent
from src.agent_logger import AgentLogger
from src.data_models import Incident, RemediationPlan

# --- Constants ---
SIMULATION_SPEED = 1.0  # seconds per tick
ANOMALY_PROBABILITY = 0.05 # 5% chance of a new anomaly per tick
RANDOM_SEED = 42
LOG_BUFFER_SIZE = 15

# --- Initialization ---
random.seed(RANDOM_SEED)
console = Console()
engine = SimulationEngine(topology_file='config/topology.json')
agent_logger = AgentLogger()
supervisor = SupervisorAgent(logger=agent_logger)
agent_logs = deque(maxlen=LOG_BUFFER_SIZE)
paused = False

# Agent pipeline state tracking
active_agent = None  # Which agent is currently processing
agent_history = []  # Track which agents have completed
current_incident = None

def make_layout() -> Layout:
    """Defines the terminal UI layout."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(name="pipeline", size=6),  # Agent pipeline visualization
        Layout(size=12, name="footer"),  # Approval prompt
    )
    layout["main"].split_row(Layout(name="left_panel"), Layout(name="right_panel"))
    layout["footer"].visible = False
    return layout

def create_status_table(telemetry_data: dict) -> Table:
    """Creates a Rich Table from telemetry data."""
    table = Table(title="Cell Tower Status", expand=True)
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Status", justify="center")
    table.add_column("Power", justify="right", style="green")
    table.add_column("Signal", justify="right", style="blue")
    table.add_column("Data", justify="right", style="yellow")

    for tower_id, metrics in telemetry_data.items():
        status = metrics['status']
        style = "green"
        if status == 'ALARM':
            style = "yellow"
        elif status == 'DOWN':
            style = "bold red"

        table.add_row(
            tower_id,
            metrics['tower_name'],
            Text(status, style=style),
            f"{metrics['power_level']:.1f}%",
            f"{metrics['signal_strength']:.1f} dBm",
            f"{metrics['data_throughput']:.1f} Mbps",
        )
    return table

def show_agent_step_through(telemetry_data: dict):
    """Show detailed step-through of agent processing."""
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/]")
    console.print("[bold cyan]DETAILED AGENT PROCESSING STEP-THROUGH[/]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════[/]\n")

    # Get all agent logs
    logs = agent_logger.get_incident_logs()

    for i, log in enumerate(logs, 1):
        agent = log['agent']
        tokens = log['tokens']
        tools = log['tools_called']
        response = log['response']

        console.print(f"[bold green]► Step {i}: {agent}[/]")
        console.print("[bold]─────────────────────────────────────────[/]")

        # Show what agent is doing
        if agent == 'DiagnosticAgent':
            console.print("[cyan]Action:[/] Diagnosing root cause from alerts")
            if tools:
                console.print(f"[cyan]Tools called:[/] {', '.join(tools)}")
            console.print(f"[cyan]Tokens used:[/] {tokens}\n")

            # Extract and show the incident object
            incident = supervisor.current_incident
            if incident:
                console.print("[bold]Incident Details:[/]")
                incident_data = {
                    "incident_type": incident.incident_type,
                    "severity": incident.severity,
                    "diagnosis_confidence": incident.diagnosis_confidence,
                    "affected_cell_ids": incident.affected_cell_ids,
                    "root_cause_hypothesis": incident.root_cause_hypothesis,
                    "evidence": incident.evidence,
                }
                console.print("[yellow]" + json.dumps(incident_data, indent=2) + "[/]\n")

            console.print("[bold green]✓ Diagnostic complete[/]")
            console.print("[cyan]Output:[/] Incident object → Remediation Agent\n")

        elif agent == 'RemediationAgent':
            console.print("[cyan]Action:[/] Creating remediation plan")
            if tools:
                console.print(f"[cyan]Tools called:[/] {', '.join(tools)}")
            console.print(f"[cyan]Tokens used:[/] {tokens}\n")

            # Extract and show the plan object
            plan = supervisor.remediation_plan
            if plan:
                console.print("[bold]Remediation Plan Details:[/]")
                plan_data = {
                    "actions": [a.description for a in plan.actions],
                    "rollback_plan": plan.rollback_plan,
                    "plan_confidence": plan.plan_confidence,
                    "verification_steps": plan.verification_steps,
                }
                console.print("[yellow]" + json.dumps(plan_data, indent=2) + "[/]\n")

            console.print("[bold green]✓ Remediation complete[/]")
            console.print("[cyan]Output:[/] RemediationPlan object → Governance Agent\n")

        elif agent == 'GovernanceAgent':
            console.print("[cyan]Action:[/] Validating against company policies")
            if tools:
                console.print(f"[cyan]Tools called:[/] {', '.join(tools)}")
            console.print(f"[cyan]Tokens used:[/] {tokens}\n")

            # Extract decision info from response text
            console.print("[bold]Governance Decision Details:[/]")
            # Try to parse decision from response
            if "APPROVE" in response.upper():
                decision_str = "APPROVE"
            elif "REJECT" in response.upper():
                decision_str = "REJECT_POLICY_VIOLATION"
            else:
                decision_str = "PENDING"

            decision_data = {
                "decision": decision_str,
                "response_summary": response[:200] + "..." if len(response) > 200 else response,
            }
            console.print("[yellow]" + json.dumps(decision_data, indent=2) + "[/]\n")

            console.print("[bold green]✓ Governance complete[/]")
            console.print("[cyan]Output:[/] GovernanceDecision → Human Approval\n")

        # Prompt to continue
        try:
            console.input(f"[bold yellow]Press Enter to continue...[/]")
        except EOFError:
            pass

def run_simulation():
    """Main function to run the simulation and render the UI."""
    global paused, active_agent, agent_history, current_incident
    layout = make_layout()
    telemetry = {} # Initialize telemetry

    # --- Guaranteed Anomaly Setup ---
    tick_counter = 0
    guaranteed_anomaly_tick = random.randint(5, 15)
    guaranteed_anomaly_injected = False
    incident_active = False
    show_step_through = False

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())

        with Live(layout, screen=True, redirect_stderr=False, vertical_overflow="visible") as live:
            while True:
                tick_counter += 1
                # --- Handle keyboard input for pausing ---
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    key = sys.stdin.read(1)
                    if key.lower() == 'p':
                        paused = not paused

                # Update header with pause status and token usage
                pause_status = "[bold red] [PAUSED][/]" if paused else ""
                token_usage = supervisor.llm_client.get_token_usage_summary()
                tokens_display = f"[cyan]Tokens: {token_usage['total_tokens']}/{supervisor.max_budget}[/]"
                header_text = Text(
                    f"Watchtower MVP - AI Self-Healing Demo {tokens_display}{pause_status}",
                    justify="center",
                    style="bold white"
                )
                layout["header"].update(Panel(header_text, style="blue"))

                # --- Run simulation step if not paused ---
                if not paused:
                    # --- Anomaly Injection ---
                    # Guaranteed first anomaly
                    if not guaranteed_anomaly_injected and tick_counter == guaranteed_anomaly_tick:
                        problem = random.choice(['POWER_OUTAGE', 'FIBER_CUT', 'SIGNAL_INTERFERENCE'])
                        engine.inject_anomaly(problem)
                        agent_logs.append(Text(f"💥 Anomaly Injected: {problem}", style="bold red"))
                        guaranteed_anomaly_injected = True
                        show_step_through = True
                    # Probabilistic subsequent anomalies
                    elif guaranteed_anomaly_injected:
                        if not engine.anomaly and random.random() < ANOMALY_PROBABILITY:
                            problem = random.choice(['POWER_OUTAGE', 'FIBER_CUT', 'SIGNAL_INTERFERENCE'])
                            engine.inject_anomaly(problem)
                            agent_logs.append(Text(f"💥 Anomaly Injected: {problem}", style="bold red"))
                            show_step_through = True

                    # Simulation and Agent Processing
                    telemetry = engine.tick()

                    # Track incident processing
                    if supervisor.current_incident and not incident_active:
                        incident_active = True
                        agent_history = []
                        active_agent = "Monitoring"
                        current_incident = supervisor.current_incident

                    # Process telemetry through agents
                    log_message = supervisor.process_telemetry(telemetry)

                    # Update agent tracking
                    if supervisor.current_incident:
                        if not agent_history:
                            agent_history.append("Monitoring")
                        if len(agent_logger.get_incident_logs()) > 0:
                            if "Diagnostic" not in agent_history:
                                agent_history.append("Diagnostic")
                                active_agent = "Diagnostic"
                            if supervisor.remediation_plan and "Remediation" not in agent_history:
                                agent_history.append("Remediation")
                                active_agent = "Remediation"
                            if supervisor.human_approval_required:
                                agent_history.append("Approval")
                                active_agent = "Approval"
                            elif "Governance" not in agent_history:
                                agent_history.append("Governance")
                                active_agent = "Governance"

                    # Reset incident when complete
                    if supervisor.human_approval_required:
                        incident_active = False

                    if log_message:
                        agent_logs.append(Text(log_message))

                # --- UI Updates ---
                status_panel = Panel(create_status_table(telemetry), title="[bold green]Live Tower Status[/bold green]")

                # Agent logs panel (renamed from "Agent Status")
                agent_logs_text = format_agent_logs(agent_logger, supervisor)
                log_panel = Panel(agent_logs_text, title="[bold blue]Agent Logs[/bold blue]")

                # Pipeline visualization
                pipeline_panel = create_pipeline_visualization(active_agent, agent_history)

                layout["left_panel"].update(status_panel)
                layout["right_panel"].update(log_panel)
                layout["pipeline"].update(pipeline_panel)

                # --- Handle Step-Through and Human Approval ---
                if supervisor.human_approval_required and show_step_through:
                    # Stop live display and show step-through
                    live.stop()

                    show_agent_step_through(telemetry)

                    plan = supervisor.remediation_plan
                    incident = supervisor.current_incident

                    # --- Show Approval Panel and Get Input ---
                    approval_text = format_approval_prompt(incident, plan)
                    console.print(Panel(approval_text, title="[bold red]Human Approval Required[/bold red]", expand=False))

                    # Restore terminal settings for the prompt and get input
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

                    # Get user input with options
                    console.print("\n[bold]Options:[/]")
                    console.print("  [bold green](y)[/] Approve plan")
                    console.print("  [bold red](n)[/] Reject - silence alert")
                    console.print("  [bold yellow](s)[/] Suggest alternative approach")
                    response = console.input("\n[bold]Your decision (y/n/s): [/]").lower().strip()

                    tty.setcbreak(sys.stdin.fileno()) # Set terminal back to cbreak mode

                    # --- Process Decision ---
                    if response == 'y':
                        # APPROVAL
                        agent_logs.append(Text(f"✅ Remediation plan APPROVED - Actions queued for execution", style="bold green"))
                        # Clear the anomaly now that it has been "handled"
                        engine.anomaly = None
                    elif response == 'n':
                        # REJECTION
                        agent_logs.append(Text(f"✅ Alert SILENCED", style="bold yellow"))
                        # Anomaly is NOT cleared, allowing it to be re-detected.
                    elif response == 's':
                        # SUGGESTION
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        suggestion = console.input("[bold]Enter your suggested approach: [/]")
                        tty.setcbreak(sys.stdin.fileno())
                        agent_logs.append(Text(f"✅ User suggested: '{suggestion}' - has been completed", style="bold cyan"))
                        engine.anomaly = None

                    # Reset state
                    supervisor.human_approval_required = False
                    supervisor.remediation_plan = None
                    supervisor.current_incident = None
                    active_agent = None
                    agent_history = []
                    current_incident = None
                    incident_active = False
                    show_step_through = False

                    # Restart the live display
                    console.clear() # Clear the prompt from the screen
                    live.start()
                    live.refresh()

                time.sleep(SIMULATION_SPEED if not paused else 0.1)

    except KeyboardInterrupt:
        pass # Gracefully exit
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def format_approval_prompt(incident: Incident, plan: RemediationPlan) -> Text:
    """Formats the text for the human approval panel."""
    incident_details = ""
    if incident:
        incident_details = (
            f"[bold]Incident ID:[/][yellow] {incident.incident_id}[/]\n"
            f"[bold]Type:[/][yellow] {incident.incident_type}[/]\n"
            f"[bold]Severity:[/][yellow] {incident.severity}[/]\n"
            f"[bold]Confidence:[/][yellow] {incident.diagnosis_confidence:.2f}[/]\n"
            f"[bold]Root Cause:[/][yellow] {incident.root_cause_hypothesis}[/]\n"
            f"[bold]Affected Cells:[/][yellow] {', '.join(incident.affected_cell_ids)}[/]\n"
        )

    plan_details = ""
    if plan and plan.actions:
        action_descriptions = "\n".join([f"- {action.description}" for action in plan.actions])
        plan_details = (
            f"[bold]Plan Confidence:[/][green] {plan.plan_confidence:.2f}[/]\n"
            f"[bold]Proposed Actions:[/]\n{action_descriptions}\n"
            f"[bold]Rollback Plan:[/][green] {plan.rollback_plan}[/]\n"
        )

    return Text.from_markup(f"{incident_details}\n{plan_details}")

def create_pipeline_visualization(active_agent: Optional[str], completed_agents: list) -> Panel:
    """Creates a visual representation of the agent pipeline."""
    agents = [
        ("Monitoring", "🔍"),
        ("Diagnostic", "🔬"),
        ("Governance", "⚖️"),
        ("Remediation", "🔧"),
        ("Approval", "✅"),
    ]

    # Build pipeline visualization with arrows
    pipeline_parts = []
    for i, (agent_name, icon) in enumerate(agents):
        # Style based on state
        if agent_name == active_agent:
            style = "bold green on black"
            text = f"[{style}] {icon} {agent_name} (ACTIVE)[/]"
        elif agent_name in completed_agents:
            style = "green"
            text = f"[{style}]✓ {agent_name}[/]"
        else:
            style = "dim white"
            text = f"[{style}]{icon} {agent_name}[/]"

        pipeline_parts.append(text)

        # Add arrow between agents
        if i < len(agents) - 1:
            # Highlight arrow if data is flowing
            if agent_name in completed_agents and agents[i+1][0] != active_agent:
                pipeline_parts.append("[green]→[/]")
            elif agent_name == active_agent:
                pipeline_parts.append("[bold green]→[/]")
            else:
                pipeline_parts.append("[dim]→[/]")

    pipeline_text = Text(" ").join([Text.from_markup(part) for part in pipeline_parts])
    return Panel(pipeline_text, title="[bold cyan]Agent Pipeline[/bold cyan]", style="cyan")

def format_agent_logs(logger, supervisor_obj) -> Text:
    """Format agent logs in natural language."""
    logs = []

    # Get agent logs from logger
    for log in logger.get_incident_logs()[-5:]:  # Last 5 interactions
        agent = log['agent']
        tokens = log['tokens']
        tools = log['tools_called']

        if agent == 'DiagnosticAgent':
            tools_str = f" using {', '.join(tools)}" if tools else ""
            logs.append(f"📊 Diagnostic team analyzing incident{tools_str}... ({tokens} tokens)")
        elif agent == 'RemediationAgent':
            logs.append(f"🛠️ Remediation team creating action plan... ({tokens} tokens)")
        elif agent == 'GovernanceAgent':
            logs.append(f"⚖️ Governance team reviewing for policy compliance... ({tokens} tokens)")

    return Text("\n".join(logs) if logs else "Initializing agents...", style="cyan")

if __name__ == "__main__":
    console.print("Starting simulation... Press 'p' to pause/resume. Press Ctrl+C to exit.", style="bold green")
    time.sleep(1)
    run_simulation()
    console.print("Simulation stopped.", style="bold green")
