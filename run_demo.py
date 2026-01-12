import time
import random
import sys
import select
import tty
import termios
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

def make_layout() -> Layout:
    """Defines the terminal UI layout."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=12, name="footer"), # Increased footer size
    )
    layout["main"].split_row(Layout(name="left_panel"), Layout(name="right_panel"))
    layout["footer"].visible = False # Hidden by default
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

def run_simulation():
    """Main function to run the simulation and render the UI."""
    global paused
    layout = make_layout()
    telemetry = {} # Initialize telemetry

    # --- Guaranteed Anomaly Setup ---
    tick_counter = 0
    guaranteed_anomaly_tick = random.randint(5, 15)
    guaranteed_anomaly_injected = False
    
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
                    # Probabilistic subsequent anomalies
                    elif guaranteed_anomaly_injected:
                        if not engine.anomaly and random.random() < ANOMALY_PROBABILITY:
                            problem = random.choice(['POWER_OUTAGE', 'FIBER_CUT', 'SIGNAL_INTERFERENCE'])
                            engine.inject_anomaly(problem)
                            agent_logs.append(Text(f"💥 Anomaly Injected: {problem}", style="bold red"))

                    # Simulation and Agent Processing
                    telemetry = engine.tick()
                    log_message = supervisor.process_telemetry(telemetry)
                    if log_message:
                        agent_logs.append(Text(log_message))

                # --- UI Updates ---
                status_panel = Panel(create_status_table(telemetry), title="[bold green]Live Tower Status[/bold green]")

                # Get agent logs from logger
                agent_log_lines = agent_logger.format_logs_for_ui(max_lines=LOG_BUFFER_SIZE)
                if agent_log_lines:
                    log_text = Text("\n".join(agent_log_lines), style="cyan")
                else:
                    log_text = Text("Waiting for incidents...", style="dim")

                log_panel = Panel(log_text, title="[bold blue]LLM Agent Activity[/bold blue]")
                layout["left_panel"].update(status_panel)
                layout["right_panel"].update(log_panel)

                # --- Handle Human Approval ---
                if supervisor.human_approval_required and not paused:
                    plan = supervisor.remediation_plan
                    incident = supervisor.current_incident
                    
                    # Stop the live display to show a clear, blocking prompt
                    live.stop()
                    
                    # --- Show Approval Panel and Get Input ---
                    approval_text = format_approval_prompt(incident, plan)
                    console.print(Panel(approval_text, title="[bold red]Human Approval Required[/bold red]", expand=False))
                    
                    # Restore terminal settings for the prompt and get input
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    approved = Confirm.ask("Do you approve this remediation plan?", console=console)
                    tty.setcbreak(sys.stdin.fileno()) # Set terminal back to cbreak mode
                    
                    # --- Process Decision ---
                    if approved:
                        agent_logs.append(Text(f"✅ Operator Approved Plan for Incident {incident.incident_id}: {plan.actions[0].description}", style="bold green"))
                        # Clear the anomaly now that it has been "handled"
                        engine.anomaly = None
                    else:
                        agent_logs.append(Text(f"❌ Operator Rejected Plan for Incident {incident.incident_id}. The problem will persist.", style="bold red"))
                        # Anomaly is NOT cleared, allowing it to be re-detected.
                    
                    # Reset state
                    supervisor.human_approval_required = False
                    supervisor.remediation_plan = None
                    supervisor.current_incident = None
                    
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

if __name__ == "__main__":
    console.print("Starting simulation... Press 'p' to pause/resume. Press Ctrl+C to exit.", style="bold green")
    time.sleep(1)
    run_simulation()
    console.print("Simulation stopped.", style="bold green")