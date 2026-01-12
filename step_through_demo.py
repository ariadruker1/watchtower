#!/usr/bin/env python3
"""Interactive step-through demo showing agent processing at each stage."""

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
import time

from src.simulation.engine import SimulationEngine
from src.agents.supervisor_agent import SupervisorAgent
from src.agents.monitoring_agent import MonitoringAgent
from src.agent_logger import AgentLogger
from src.data_models import Alert

console = Console()

class StepThroughDemo:
    def __init__(self):
        self.logger = AgentLogger()
        self.supervisor = SupervisorAgent(logger=self.logger)
        self.monitoring_agent = MonitoringAgent()
        self.engine = SimulationEngine(topology_file='config/topology.json')

        # State tracking
        self.current_stage = 0
        self.stages = []
        self.telemetry = None
        self.alerts = None
        self.incident = None
        self.remediation_plan = None
        self.governance_decision = None

    def detect_anomaly(self, anomaly_type: str):
        """Inject anomaly and detect with monitoring agent."""
        console.print("\n[bold cyan]═══════════════════════════════════════════════════════════[/]")
        console.print("[bold cyan]DETECTING ANOMALY[/]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════[/]\n")

        # Inject anomaly
        self.engine.inject_anomaly(anomaly_type)
        self.telemetry = self.engine.tick()

        # Show affected towers
        console.print("[bold]Telemetry Status:[/]")
        affected_towers = []
        for tower_id, metrics in self.telemetry.items():
            if metrics['status'] != 'OK':
                affected_towers.append(tower_id)
                status_color = "red" if metrics['status'] == 'DOWN' else "yellow"
                console.print(
                    f"  [bold {status_color}]●[/] {tower_id}: {metrics['status']} "
                    f"(Power: {metrics['power_level']:.1f}%, Signal: {metrics['signal_strength']:.1f} dBm)"
                )

        if affected_towers:
            console.print(f"\n[bold green]✓ Anomaly detected in {len(affected_towers)} tower(s)[/]\n")
        else:
            console.print("\n[bold yellow]⚠ No anomalies detected[/]\n")
            return False

        # Initialize stages
        self.current_stage = 0
        self.stages = [
            {
                'name': 'MONITORING',
                'status': 'pending',
                'description': 'Analyzing telemetry for alerts',
                'log': [],
            },
            {
                'name': 'DIAGNOSTIC',
                'status': 'pending',
                'description': 'Diagnosing root cause of alerts',
                'log': [],
            },
            {
                'name': 'REMEDIATION',
                'status': 'pending',
                'description': 'Creating remediation plan',
                'log': [],
            },
            {
                'name': 'GOVERNANCE',
                'status': 'pending',
                'description': 'Validating against company policies',
                'log': [],
            },
        ]

        return True

    def step_monitoring(self):
        """Execute monitoring stage."""
        stage = self.stages[self.current_stage]
        stage['status'] = 'active'

        console.print(self._render_pipeline())
        console.print("\n[bold green]► MONITORING AGENT[/]")
        console.print("[bold]─────────────────────────────────────────[/]")

        # Log what monitoring is doing
        console.print("[cyan]Action:[/] Analyzing telemetry data for threshold violations")
        time.sleep(0.5)

        # Get alerts
        self.alerts = self.monitoring_agent.analyze_telemetry(self.telemetry)

        # Log results
        stage['log'].append(f"Scanned telemetry data from {len(self.telemetry)} towers")
        console.print(f"  → Scanned {len(self.telemetry)} towers")
        time.sleep(0.3)

        stage['log'].append(f"Detected {len(self.alerts)} alerts from threshold violations")
        console.print(f"  → Found {len(self.alerts)} alerts:")
        for alert in self.alerts[:5]:  # Show first 5
            console.print(f"     • {alert.tower_id}: {alert.message}")
        if len(self.alerts) > 5:
            console.print(f"     ... and {len(self.alerts) - 5} more")
        time.sleep(0.5)

        # Prepare to pass to diagnostic
        stage['log'].append(f"Passing {len(self.alerts)} alerts to Diagnostic Agent")
        console.print(f"\n[bold green]✓ Monitoring complete[/]")
        console.print(f"[cyan]Output:[/] {len(self.alerts)} alerts → Diagnostic Agent\n")

        stage['status'] = 'complete'
        self._prompt_continue("Diagnostic Agent")

    def step_diagnostic(self):
        """Execute diagnostic stage."""
        stage = self.stages[self.current_stage]
        stage['status'] = 'active'

        console.print(self._render_pipeline())
        console.print("\n[bold green]► DIAGNOSTIC AGENT[/]")
        console.print("[bold]─────────────────────────────────────────[/]")

        console.print("[cyan]Action:[/] Diagnosing root cause from alerts")
        time.sleep(0.5)

        # Log tool calls
        console.print("[cyan]Tools being called:[/]")
        tools_to_call = [
            ("get_weather_at_tower", "Checking weather conditions"),
            ("get_tower_maintenance_history", "Checking maintenance history"),
            ("check_regional_news_alerts", "Checking for regional events"),
        ]

        for tool_name, description in tools_to_call:
            console.print(f"  • {tool_name}: {description}")
            time.sleep(0.3)

        stage['log'].append("Called 3 diagnostic tools to gather evidence")
        time.sleep(0.5)

        # Run diagnosis
        console.print("\n[cyan]Analysis:[/] Processing tool results...")
        time.sleep(0.3)

        self.incident = self.supervisor.diagnostic_agent.diagnose_alerts(self.alerts)

        if self.incident:
            stage['log'].append(f"Diagnosed: {self.incident.incident_type}")
            console.print(f"  → Incident Type: [bold cyan]{self.incident.incident_type}[/]")
            time.sleep(0.2)

            stage['log'].append(f"Confidence: {self.incident.diagnosis_confidence:.0%}")
            console.print(f"  → Confidence: {self.incident.diagnosis_confidence:.0%}")
            time.sleep(0.2)

            stage['log'].append(f"Root Cause: {self.incident.root_cause_hypothesis}")
            console.print(f"  → Root Cause: {self.incident.root_cause_hypothesis[:60]}...")
            time.sleep(0.2)

            stage['log'].append(f"Severity: {self.incident.severity}")
            console.print(f"  → Severity: [bold yellow]{self.incident.severity}[/]")
        else:
            stage['log'].append("Unable to diagnose - no clear root cause identified")
            console.print("[bold red]✗ Unable to diagnose incident[/]")

        time.sleep(0.5)
        stage['log'].append(f"Passing diagnosis to Remediation Agent")
        console.print(f"\n[bold green]✓ Diagnostic complete[/]")
        console.print(f"[cyan]Output:[/] Incident object → Remediation Agent\n")

        stage['status'] = 'complete'
        self._prompt_continue("Remediation Agent")

    def step_remediation(self):
        """Execute remediation stage."""
        stage = self.stages[self.current_stage]
        stage['status'] = 'active'

        console.print(self._render_pipeline())
        console.print("\n[bold green]► REMEDIATION AGENT[/]")
        console.print("[bold]─────────────────────────────────────────[/]")

        if not self.incident:
            console.print("[bold red]✗ No incident to remediate - skipping[/]\n")
            stage['status'] = 'skipped'
            self._prompt_continue("Governance Agent")
            return

        console.print("[cyan]Action:[/] Creating remediation plan for incident")
        time.sleep(0.5)

        console.print("[cyan]Tools being called:[/]")
        tools_to_call = [
            ("get_standard_operating_procedure", "Fetching incident runbook"),
            ("get_on_call_engineer_schedule", "Checking available teams"),
        ]

        for tool_name, description in tools_to_call:
            console.print(f"  • {tool_name}: {description}")
            time.sleep(0.3)

        stage['log'].append("Called 2 remediation tools for guidance")
        time.sleep(0.5)

        console.print("\n[cyan]Planning:[/] Creating action steps...")
        time.sleep(0.3)

        self.remediation_plan = self.supervisor.remediation_agent.create_plan(self.incident)

        if self.remediation_plan:
            stage['log'].append(f"Created plan with {len(self.remediation_plan.actions)} action(s)")
            console.print(f"  → Plan includes {len(self.remediation_plan.actions)} action(s):")
            for i, action in enumerate(self.remediation_plan.actions, 1):
                console.print(f"     {i}. {action.description[:70]}...")
                time.sleep(0.2)

            stage['log'].append(f"Plan confidence: {self.remediation_plan.plan_confidence:.0%}")
            console.print(f"  → Plan Confidence: {self.remediation_plan.plan_confidence:.0%}")
            time.sleep(0.2)

            stage['log'].append(f"Rollback: {self.remediation_plan.rollback_plan}")
            console.print(f"  → Rollback Procedure: {self.remediation_plan.rollback_plan[:50]}...")
        else:
            stage['log'].append("Unable to create remediation plan")
            console.print("[bold red]✗ Unable to create plan[/]")

        time.sleep(0.5)
        stage['log'].append("Passing plan to Governance Agent for validation")
        console.print(f"\n[bold green]✓ Remediation complete[/]")
        console.print(f"[cyan]Output:[/] RemediationPlan object → Governance Agent\n")

        stage['status'] = 'complete'
        self._prompt_continue("Governance Agent")

    def step_governance(self):
        """Execute governance stage."""
        stage = self.stages[self.current_stage]
        stage['status'] = 'active'

        console.print(self._render_pipeline())
        console.print("\n[bold green]► GOVERNANCE AGENT[/]")
        console.print("[bold]─────────────────────────────────────────[/]")

        if not self.remediation_plan:
            console.print("[bold red]✗ No plan to evaluate - skipping[/]\n")
            stage['status'] = 'skipped'
            return

        console.print("[cyan]Action:[/] Validating remediation plan against company policies")
        time.sleep(0.5)

        console.print("[cyan]Tools being called:[/]")
        console.print(f"  • get_company_policy_document: Checking policy compliance")
        time.sleep(0.3)

        stage['log'].append("Checking company policy compliance")
        time.sleep(0.5)

        console.print("\n[cyan]Evaluation:[/] Assessing plan against policies...")
        time.sleep(0.3)

        self.governance_decision = self.supervisor.governance_agent.evaluate(
            self.incident,
            self.remediation_plan
        )

        if self.governance_decision:
            stage['log'].append(f"Decision: {self.governance_decision.decision}")

            decision_color = "green" if self.governance_decision.decision == "APPROVE" else "red"
            console.print(f"  → Decision: [bold {decision_color}]{self.governance_decision.decision}[/]")
            time.sleep(0.2)

            stage['log'].append(f"Reason: {self.governance_decision.reason}")
            console.print(f"  → Reason: {self.governance_decision.reason[:60]}...")
            time.sleep(0.2)

            stage['log'].append(f"Policies checked: {', '.join(self.governance_decision.policies_checked)}")
            console.print(f"  → Policies checked: {len(self.governance_decision.policies_checked)}")

        time.sleep(0.5)
        if self.governance_decision.decision == "APPROVE":
            stage['log'].append("Plan approved - ready for human review")
            console.print(f"\n[bold green]✓ Governance validation complete[/]")
            console.print(f"[cyan]Output:[/] APPROVED - Awaiting human approval\n")
        else:
            stage['log'].append(f"Plan rejected: {self.governance_decision.reason}")
            console.print(f"\n[bold red]✗ Plan rejected[/]")
            console.print(f"[cyan]Output:[/] REJECTED - Manual review required\n")

        stage['status'] = 'complete'

    def _prompt_continue(self, next_stage: str):
        """Prompt user to continue, gracefully handle EOF."""
        try:
            console.input(f"[bold yellow]Press Enter to continue to {next_stage}...[/]")
        except EOFError:
            # Auto-continue when piped
            console.print(f"[bold yellow](Auto-continuing to {next_stage}...)[/]")

    def _render_pipeline(self) -> Panel:
        """Render the agent pipeline with status."""
        pipeline_text = ""

        for i, stage in enumerate(self.stages):
            # Status indicator
            if stage['status'] == 'active':
                indicator = "[bold green]●[/]"
                color = "green"
            elif stage['status'] == 'complete':
                indicator = "[bold green]✓[/]"
                color = "green"
            elif stage['status'] == 'skipped':
                indicator = "[bold yellow]⊘[/]"
                color = "yellow"
            else:  # pending
                indicator = "[bold white]○[/]"
                color = "white"

            stage_name = f"[bold {color}]{stage['name']}[/]"
            pipeline_text += f"{indicator} {stage_name}"

            if i < len(self.stages) - 1:
                arrow = " [bold green]→[/] " if stage['status'] in ['complete', 'active'] else " [bold white]→[/] "
                pipeline_text += arrow

        return Panel(pipeline_text, title="[bold]Agent Pipeline[/]", expand=False)

    def run(self):
        """Run the interactive step-through demo."""
        console.print("\n[bold cyan]╔═══════════════════════════════════════════════════════════╗[/]")
        console.print("[bold cyan]║     WATCHTOWER MVP - INTERACTIVE STEP-THROUGH DEMO       ║[/]")
        console.print("[bold cyan]╚═══════════════════════════════════════════════════════════╝[/]\n")

        console.print("[yellow]Choose an anomaly type to inject:[/]")
        console.print("  1. POWER_OUTAGE")
        console.print("  2. FIBER_CUT")
        console.print("  3. SIGNAL_INTERFERENCE\n")

        try:
            choice = console.input("[bold]Enter choice (1-3): [/]")
        except EOFError:
            choice = "1"
            console.print("[bold yellow](Using default: POWER_OUTAGE)[/]")

        anomaly_map = {
            '1': 'POWER_OUTAGE',
            '2': 'FIBER_CUT',
            '3': 'SIGNAL_INTERFERENCE',
        }

        anomaly_type = anomaly_map.get(choice, 'POWER_OUTAGE')

        # Detect anomaly
        if not self.detect_anomaly(anomaly_type):
            console.print("[bold red]No anomalies detected. Exiting.[/]\n")
            return

        # Step through each stage
        while self.current_stage < len(self.stages):
            stage = self.stages[self.current_stage]

            if stage['name'] == 'MONITORING':
                self.step_monitoring()
            elif stage['name'] == 'DIAGNOSTIC':
                self.step_diagnostic()
            elif stage['name'] == 'REMEDIATION':
                self.step_remediation()
            elif stage['name'] == 'GOVERNANCE':
                self.step_governance()

            self.current_stage += 1

        # Final summary
        console.print(self._render_pipeline())
        console.print("\n[bold green]═════════════════════════════════════════════════════════════[/]")
        console.print("[bold green]INCIDENT PROCESSING COMPLETE[/]")
        console.print("[bold green]═════════════════════════════════════════════════════════════[/]\n")

        # Show final summary
        console.print("[bold]Final Summary:[/]")
        console.print(f"  • Incident Type: {self.incident.incident_type if self.incident else 'N/A'}")
        console.print(f"  • Diagnosis Confidence: {self.incident.diagnosis_confidence:.0%}" if self.incident else "  • No incident diagnosed")
        console.print(f"  • Remediation Plan: {'Created' if self.remediation_plan else 'Not created'}")
        console.print(f"  • Governance Decision: {self.governance_decision.decision if self.governance_decision else 'N/A'}")

        # Token usage
        token_usage = self.supervisor.llm_client.get_token_usage_summary()
        console.print(f"\n[cyan]Token Usage:[/] {token_usage['total_tokens']}/{self.supervisor.max_budget} tokens")
        console.print(f"[cyan]API Calls:[/] {token_usage['calls_made']} LLM calls\n")

if __name__ == "__main__":
    demo = StepThroughDemo()
    demo.run()
