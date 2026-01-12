#!/usr/bin/env python3
"""Simple demo of the Watchtower MVP agent flow without interactive terminal."""

from dotenv import load_dotenv
load_dotenv()

from src.simulation.engine import SimulationEngine
from src.agents.supervisor_agent import SupervisorAgent
from src.agent_logger import AgentLogger
import time

def main():
    """Run a simple demo of incident response."""
    print("\n" + "="*60)
    print("  WATCHTOWER MVP - AI SELF-HEALING NETWORK DEMO")
    print("="*60 + "\n")

    # Initialize
    logger = AgentLogger()
    supervisor = SupervisorAgent(logger=logger)
    engine = SimulationEngine(topology_file='config/topology.json')

    # Run multiple test scenarios
    scenarios = [
        ('POWER_OUTAGE', 'Simulating power outage'),
        ('FIBER_CUT', 'Simulating fiber cut'),
        ('SIGNAL_INTERFERENCE', 'Simulating signal interference'),
    ]

    for scenario_type, description in scenarios:
        print(f"\n{'─'*60}")
        print(f"Scenario: {description}")
        print(f"{'─'*60}")

        # Inject anomaly and get telemetry
        engine.inject_anomaly(scenario_type)
        telemetry = engine.tick()

        # Show affected towers
        print("\nTelemetry Status:")
        for tower_id, metrics in telemetry.items():
            if metrics['status'] != 'OK':
                print(f"  {tower_id}: {metrics['status']} "
                      f"(Power: {metrics['power_level']:.1f}%, Signal: {metrics['signal_strength']:.1f} dBm)")

        # Process through supervisor
        print("\nProcessing through agent pipeline...")
        result = supervisor.process_telemetry(telemetry)
        print(f"  Result: {result}")

        # Show incident details if diagnosed
        if supervisor.current_incident:
            print(f"\n✓ Incident Diagnosed:")
            print(f"  Type: {supervisor.current_incident.incident_type}")
            print(f"  Confidence: {supervisor.current_incident.diagnosis_confidence:.2f}")
            print(f"  Severity: {supervisor.current_incident.severity}")
            print(f"  Root Cause: {supervisor.current_incident.root_cause_hypothesis}")

            if supervisor.remediation_plan:
                print(f"\n✓ Remediation Plan Created:")
                print(f"  Actions: {len(supervisor.remediation_plan.actions)}")
                for i, action in enumerate(supervisor.remediation_plan.actions[:3], 1):
                    print(f"    {i}. {action.description[:60]}...")
                if supervisor.human_approval_required:
                    print(f"  ✓ Awaiting human approval")

        # Show token usage
        token_usage = supervisor.llm_client.get_token_usage_summary()
        print(f"\nToken Usage: {token_usage['total_tokens']}/{supervisor.max_budget} tokens")

        # Show agent logs
        print(f"\nAgent Interactions:")
        for log in logger.current_incident_logs:
            tools_info = f" | Tools: {', '.join(log['tools_called'])}" if log['tools_called'] else ""
            print(f"  • {log['agent']}: {log['tokens']} tokens{tools_info}")

        time.sleep(1)  # Brief pause between scenarios

    print(f"\n{'='*60}")
    print("  Demo Complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
