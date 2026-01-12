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

# Step-through state tracking
step_through_mode = False
current_step_index = 0
step_through_data = []
awaiting_step_advance = False
agents_active = False  # True when diagnostic agent starts processing
log_scroll_offset = 0  # Scroll position in agent logs
full_log_history = deque(maxlen=1000)  # Keep all log messages ever displayed
viewing_full_log = False  # True when 'l' is pressed to show full history
loading_llm = False  # True when waiting for LLM response
llm_load_spinner = 0  # Spinner animation frame

def read_key_with_escape() -> str:
    """Read a key, handling escape sequences for arrow keys."""
    try:
        ch = sys.stdin.read(1)
        if not ch:
            return ''

        if ch == '\x1b':  # ESC sequence
            try:
                next_ch = sys.stdin.read(1)
                if next_ch == '[':
                    final_ch = sys.stdin.read(1)
                    if final_ch == 'A':
                        return 'UP'
                    elif final_ch == 'B':
                        return 'DOWN'
                    elif final_ch == 'C':
                        return 'RIGHT'
                    elif final_ch == 'D':
                        return 'LEFT'
            except:
                pass
            return 'ESC'

        return ch
    except:
        return ''

def make_layout() -> Layout:
    """Defines the terminal UI layout."""
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="pipeline", size=5),
        Layout(name="approval", size=10),
        Layout(name="help", size=3),  # Increased size for help panel
    )
    layout["main"].split_row(
        Layout(name="left_panel", ratio=1),
        Layout(name="right_panel", ratio=1)
    )
    layout["approval"].visible = False

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

def generate_step_through_data(telemetry_data: dict) -> list:
    """Generate step-through data for each agent processing step.

    Returns a list of step dictionaries, each containing the formatted step text.
    """
    steps = []
    logs = agent_logger.get_incident_logs()

    for i, log in enumerate(logs, 1):
        agent = log['agent']
        tokens = log['tokens']
        tools = log['tools_called']
        response = log['response']

        step_text = f"[bold green]► Step {i}: {agent}[/]\n"
        step_text += "[bold]─────────────────────────────────────────[/]\n"

        # Show what agent is doing
        if agent == 'DiagnosticAgent':
            step_text += "[cyan]Action:[/] Diagnosing root cause from alerts\n"
            if tools:
                step_text += f"[cyan]Tools called:[/] {', '.join(tools)}\n"
            step_text += f"[cyan]Tokens used:[/] {tokens}\n\n"

            # Extract and show the incident object
            incident = supervisor.current_incident
            if incident:
                step_text += "[bold]Incident Details:[/]\n"
                incident_data = {
                    "incident_type": incident.incident_type,
                    "severity": incident.severity,
                    "diagnosis_confidence": incident.diagnosis_confidence,
                    "affected_cell_ids": incident.affected_cell_ids,
                    "root_cause_hypothesis": incident.root_cause_hypothesis,
                    "evidence": incident.evidence,
                }
                step_text += "[yellow]" + json.dumps(incident_data, indent=2) + "[/]\n\n"

            step_text += "[bold green]✓ Diagnostic complete[/]\n"
            step_text += "[cyan]Output:[/] Incident object → Remediation Agent"

        elif agent == 'RemediationAgent':
            step_text += "[cyan]Action:[/] Creating remediation plan\n"
            if tools:
                step_text += f"[cyan]Tools called:[/] {', '.join(tools)}\n"
            step_text += f"[cyan]Tokens used:[/] {tokens}\n\n"

            # Extract and show the plan object
            plan = supervisor.remediation_plan
            if plan:
                step_text += "[bold]Remediation Plan Details:[/]\n"
                plan_data = {
                    "actions": [a.description for a in plan.actions],
                    "rollback_plan": plan.rollback_plan,
                    "plan_confidence": plan.plan_confidence,
                    "verification_steps": plan.verification_steps,
                }
                step_text += "[yellow]" + json.dumps(plan_data, indent=2) + "[/]\n\n"

            step_text += "[bold green]✓ Remediation complete[/]\n"
            step_text += "[cyan]Output:[/] RemediationPlan object → Governance Agent"

        elif agent == 'GovernanceAgent':
            step_text += "[cyan]Action:[/] Validating against company policies\n"
            if tools:
                step_text += f"[cyan]Tools called:[/] {', '.join(tools)}\n"
            step_text += f"[cyan]Tokens used:[/] {tokens}\n\n"

            # Extract decision info from response text
            step_text += "[bold]Governance Decision Details:[/]\n"
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
            step_text += "[yellow]" + json.dumps(decision_data, indent=2) + "[/]\n\n"

            step_text += "[bold green]✓ Governance complete[/]\n"
            step_text += "[cyan]Output:[/] GovernanceDecision → Human Approval"

        steps.append({"index": i, "agent": agent, "text": step_text})

    return steps

def run_simulation():
    """Main function to run the simulation and render the UI."""
    global paused, active_agent, agent_history, current_incident
    global step_through_mode, current_step_index, step_through_data, awaiting_step_advance
    global agents_active, log_scroll_offset, viewing_full_log, loading_llm, llm_load_spinner
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
                llm_load_spinner += 1  # Animate spinner

                # --- Handle keyboard input ---
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    key = read_key_with_escape()

                    if key:  # Only process non-empty keys
                        # Handle space bar for stepping through steps
                        if key == ' ' and step_through_mode and awaiting_step_advance:
                            if current_step_index < len(step_through_data) - 1:
                                current_step_index += 1
                            else:
                                awaiting_step_advance = False
                                layout["approval"].visible = True

                        # Handle full log viewing
                        if key.lower() == 'l' and agents_active and not viewing_full_log:
                            viewing_full_log = True
                            log_scroll_offset = 0

                        # Handle ESC to exit log view
                        if key == 'ESC':
                            viewing_full_log = False
                            log_scroll_offset = 0

                        # Handle scrolling in full log view
                        if viewing_full_log:
                            if key == 'UP':
                                log_scroll_offset = max(0, log_scroll_offset - 3)
                            elif key == 'DOWN':
                                log_scroll_offset += 3

                        # Handle pause
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

                # --- Run simulation step if not paused and agents not active ---
                if not paused and not agents_active:
                    # --- Anomaly Injection ---
                    # Guaranteed first anomaly
                    if not guaranteed_anomaly_injected and tick_counter == guaranteed_anomaly_tick:
                        problem = random.choice(['POWER_OUTAGE', 'FIBER_CUT', 'SIGNAL_INTERFERENCE'])
                        engine.inject_anomaly(problem)
                        agent_logs.append(Text(f"💥 Anomaly Injected: {problem}", style="bold red"))
                        full_log_history.append(f"💥 Anomaly Injected: {problem}")
                        guaranteed_anomaly_injected = True
                        show_step_through = True
                    # Probabilistic subsequent anomalies
                    elif guaranteed_anomaly_injected:
                        if not engine.anomaly and random.random() < ANOMALY_PROBABILITY:
                            problem = random.choice(['POWER_OUTAGE', 'FIBER_CUT', 'SIGNAL_INTERFERENCE'])
                            engine.inject_anomaly(problem)
                            agent_logs.append(Text(f"💥 Anomaly Injected: {problem}", style="bold red"))
                            full_log_history.append(f"💥 Anomaly Injected: {problem}")
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
                                agents_active = True  # Pause simulation when diagnostic starts
                                loading_llm = True
                                paused = True
                            if supervisor.remediation_plan and "Remediation" not in agent_history:
                                agent_history.append("Remediation")
                                active_agent = "Remediation"
                                loading_llm = False
                            if "Governance" not in agent_history:
                                agent_history.append("Governance")
                                active_agent = "Governance"
                                loading_llm = True
                            if supervisor.human_approval_required:
                                agent_history.append("Approval")
                                active_agent = "Approval"
                                loading_llm = False

                    # Reset incident when complete
                    if supervisor.human_approval_required:
                        incident_active = False

                    if log_message:
                        agent_logs.append(Text(log_message))
                        full_log_history.append(log_message)

                # --- UI Updates ---
                status_panel = Panel(create_status_table(telemetry), title="[bold green]Live Tower Status[/bold green]")

                # Agent logs panel (renamed from "Agent Status")
                agent_logs_text = format_agent_logs(agent_logger, supervisor)
                log_panel = Panel(agent_logs_text, title="[bold blue]Agent Logs[/bold blue]")

                # Pipeline visualization
                pipeline_panel = create_pipeline_visualization(active_agent, agent_history)

                # Always update help panel with current controls
                help_text = "[bold cyan]SPACE[/] step  |  [bold cyan]↑↓[/] scroll  |  [bold cyan]l[/] log  |  [bold cyan]esc[/] close  |  [bold green]y[/] approve  |  [bold red]n[/] reject  |  [bold yellow]p[/] pause"
                layout["help"].update(Panel(help_text, title="[bold cyan]COMMANDS[/bold cyan]", style="cyan"))

                layout["left_panel"].update(status_panel)
                layout["right_panel"].update(log_panel)
                layout["pipeline"].update(pipeline_panel)

                # --- Handle Step-Through Mode ---
                if supervisor.human_approval_required and show_step_through and not step_through_mode:
                    # Enter step-through mode and generate data
                    step_through_mode = True
                    current_step_index = 0
                    step_through_data = generate_step_through_data(telemetry)
                    awaiting_step_advance = True
                    loading_llm = False  # We're now showing the completed processing

                # --- Handle Step-Through keyboard input (if not already handled above) ---
                # This is handled in the main keyboard input section above

                # --- Handle Approval Prompt in Approval Panel ---
                if step_through_mode and not awaiting_step_advance and supervisor.human_approval_required:
                    plan = supervisor.remediation_plan
                    incident = supervisor.current_incident
                    approval_text = format_approval_prompt(incident, plan)

                    approval_panel_text = Text.from_markup(
                        "[bold]Options:[/]\n"
                        "  [bold green](y)[/] Approve and enact plan\n"
                        "  [bold red](n)[/] Reject and silence alarm\n\n"
                        "[bold]Your decision (y/n): [/]"
                    )
                    approval_full = Text("\n").join([approval_text, approval_panel_text])
                    layout["approval"].update(Panel(approval_full, title="[bold red]Human Approval Required[/bold red]"))
                    layout["approval"].visible = True

                    # Handle approval input - check for keys in step-through mode
                    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        key = read_key_with_escape()

                        if key and key.lower() in ['y', 'n']:
                            response = key.lower()

                            if response == 'y':
                                # APPROVAL - format the plan nicely
                                plan_actions = ""
                                if plan and plan.actions:
                                    plan_actions = " - " + ", ".join([a.description for a in plan.actions[:2]])
                                approval_msg = f"✅ Remediation plan has been enacted{plan_actions}"
                                agent_logs.append(Text(approval_msg, style="bold green"))
                                full_log_history.append(approval_msg)
                                engine.anomaly = None
                                step_through_mode = False
                                current_step_index = 0
                                step_through_data = []
                                layout["approval"].visible = False
                                supervisor.human_approval_required = False
                                supervisor.remediation_plan = None
                                supervisor.current_incident = None
                                active_agent = None
                                agent_history = []
                                current_incident = None
                                incident_active = False
                                show_step_through = False
                                agents_active = False
                                log_scroll_offset = 0
                                viewing_full_log = False

                            elif response == 'n':
                                # REJECTION - show which alarm was silenced
                                incident_type = incident.incident_type if incident else "Unknown incident"
                                rejection_msg = f"✅ {incident_type} alarm was silenced"
                                agent_logs.append(Text(rejection_msg, style="bold yellow"))
                                full_log_history.append(rejection_msg)
                                step_through_mode = False
                                current_step_index = 0
                                step_through_data = []
                                layout["approval"].visible = False
                                supervisor.human_approval_required = False
                                supervisor.remediation_plan = None
                                supervisor.current_incident = None
                                active_agent = None
                                agent_history = []
                                current_incident = None
                                incident_active = False
                                show_step_through = False
                                agents_active = False
                                log_scroll_offset = 0
                                viewing_full_log = False

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
        ("Remediation", "🔧"),
        ("Governance", "⚖️"),
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
            # Highlight arrow based on agent state
            if agent_name in completed_agents:
                pipeline_parts.append("[green]→[/]")
            elif agent_name == active_agent:
                pipeline_parts.append("[bold green]→[/]")
            else:
                pipeline_parts.append("[dim]→[/]")

    pipeline_text = Text(" ").join([Text.from_markup(part) for part in pipeline_parts])
    return Panel(pipeline_text, title="[bold cyan]Agent Pipeline[/bold cyan]", style="cyan")

def format_agent_logs(logger, supervisor_obj) -> Text:
    """Format agent logs in natural language or detailed step-through with scrolling support."""
    global llm_load_spinner

    # If agents are active and not yet in step-through, show loading
    if agents_active and not step_through_mode and loading_llm:
        spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        spinner_char = spinners[llm_load_spinner % len(spinners)]
        loading_msg = (
            f"{spinner_char} Simulation paused - processing with AI agents...\n\n"
            f"• Diagnostic agent analyzing incident\n"
            f"• Generating remediation strategies\n"
            f"• Reviewing policy compliance\n\n"
            f"[bold cyan]Awaiting agent response...[/bold cyan]"
        )
        return Text.from_markup(loading_msg)

    # If viewing full log history
    if viewing_full_log:
        log_lines = list(full_log_history)
        if not log_lines:
            return Text("No log history available", style="cyan")

        # Apply scroll offset
        visible_lines = log_lines[log_scroll_offset:]
        display_text = "\n".join(visible_lines)
        display_text += f"\n\n[dim]Position: {log_scroll_offset} | Use ↑↓ to scroll[/dim]"
        return Text.from_markup(display_text)

    # If in step-through mode, show current step with navigation hint
    if step_through_mode and step_through_data:
        current_step = step_through_data[current_step_index]
        step_text = current_step["text"]

        # Add loading indicator if still processing
        if loading_llm:
            spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            spinner_char = spinners[llm_load_spinner % len(spinners)]
            step_text += f"\n\n[bold yellow]{spinner_char} Processing with LLM...[/bold yellow]"

        # Add navigation hint
        if current_step_index < len(step_through_data) - 1:
            step_text += "\n\n[bold green]→ Press SPACE to advance to next step[/bold green]"
        else:
            step_text += "\n\n[bold green]→ Press SPACE to show approval options[/bold green]"

        return Text.from_markup(step_text)

    # Default mode: show regular agent logs
    logs = []

    # Get agent logs from logger
    for log in logger.get_incident_logs()[-5:]:  # Last 5 interactions
        agent = log['agent']
        tokens = log['tokens']
        tools = log['tools_called']

        if agent == 'DiagnosticAgent':
            tools_str = f"\n    Tools used: {', '.join(tools)}" if tools else ""
            log_msg = f"• Root cause analysis performed{tools_str}\n    Tokens: {tokens}"
            logs.append(log_msg)
            full_log_history.append(log_msg)
        elif agent == 'RemediationAgent':
            log_msg = f"• Remediation action plan generated\n    Tokens: {tokens}"
            logs.append(log_msg)
            full_log_history.append(log_msg)
        elif agent == 'GovernanceAgent':
            log_msg = f"• Policy compliance review completed\n    Tokens: {tokens}"
            logs.append(log_msg)
            full_log_history.append(log_msg)

    return Text("\n".join(logs) if logs else "Initializing agents...", style="cyan")

if __name__ == "__main__":
    console.print("Starting simulation... Press 'p' to pause/resume. Press Ctrl+C to exit.", style="bold green")
    time.sleep(1)
    run_simulation()
    console.print("Simulation stopped.", style="bold green")
