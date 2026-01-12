#!/usr/bin/env python3
"""Simple test to verify agent flow completes end-to-end."""

import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.agents.supervisor_agent import SupervisorAgent
from src.agent_logger import AgentLogger
from src.simulation.engine import SimulationEngine

def test_agent_flow():
    """Test that the agent flow completes through all stages."""
    print("\n=== Agent Flow Test ===\n")

    # Initialize
    logger = AgentLogger()
    supervisor = SupervisorAgent(logger=logger)
    engine = SimulationEngine(topology_file='config/topology.json')

    # Get telemetry with a guaranteed power outage anomaly
    print("1. Generating telemetry with POWER_OUTAGE anomaly...")

    # Inject a power outage anomaly
    engine.inject_anomaly('POWER_OUTAGE')
    telemetry = engine.tick()

    # Get the affected tower
    affected_tower = None
    for tower_id, metrics in telemetry.items():
        if metrics['status'] == 'DOWN':
            affected_tower = tower_id
            break

    if affected_tower:
        print(f"   Tower {affected_tower} status: {telemetry[affected_tower]['status']}")
        print(f"   Power level: {telemetry[affected_tower]['power_level']}%")
    else:
        print("   No anomaly detected, using tower_1")
        affected_tower = 'tower_1'

    # Process through supervisor
    print("\n2. Processing through Supervisor Agent...")
    result = supervisor.process_telemetry(telemetry)
    print(f"\n   Supervisor Result:\n   {result}")

    # Check agent states
    print("\n3. Agent Flow Status:")
    print(f"   - Current Incident: {supervisor.current_incident}")
    if supervisor.current_incident:
        print(f"     Type: {supervisor.current_incident.incident_type}")
        print(f"     Confidence: {supervisor.current_incident.diagnosis_confidence:.2f}")
        print(f"     Severity: {supervisor.current_incident.severity}")

    print(f"\n   - Remediation Plan: {supervisor.remediation_plan}")
    if supervisor.remediation_plan:
        print(f"     Actions: {len(supervisor.remediation_plan.actions)}")
        for i, action in enumerate(supervisor.remediation_plan.actions):
            print(f"       {i+1}. {action.description}")

    print(f"\n   - Human Approval Required: {supervisor.human_approval_required}")

    # Check token usage
    token_usage = supervisor.llm_client.get_token_usage_summary()
    print(f"\n4. Token Usage:")
    print(f"   - Total: {token_usage['total_tokens']}")
    print(f"   - Calls Made: {token_usage['calls_made']}")
    print(f"   - Avg per Call: {token_usage['avg_tokens_per_call']:.1f}")
    print(f"   - Budget: {supervisor.max_budget}")
    print(f"   - Remaining: {supervisor.max_budget - token_usage['total_tokens']}")

    # Check logs
    print(f"\n5. Agent Logs ({len(logger.interactions)} total):")
    for log in logger.interactions[-5:]:  # Show last 5 logs
        print(f"   - {log['agent']}: {log['tokens']} tokens, success={log['success']}")
        if log['tools_called']:
            print(f"     Tools: {', '.join(log['tools_called'])}")
        print(f"     Response: {log['response'][:150]}")

    # Determine success
    success = (
        supervisor.current_incident is not None and
        supervisor.remediation_plan is not None and
        supervisor.human_approval_required
    )

    print(f"\n=== Test Result: {'✓ PASSED' if success else '✗ FAILED'} ===\n")
    return success

if __name__ == "__main__":
    try:
        success = test_agent_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
