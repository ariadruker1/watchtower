#!/usr/bin/env python3
"""Test diagnostic agent directly with debugging."""

import json
from dotenv import load_dotenv

load_dotenv()

from src.agents.diagnostic_agent import DiagnosticAgent
from src.data_models import Alert
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
import time

def test_diagnostic():
    """Test diagnostic agent directly."""
    print("\n=== Diagnostic Agent Direct Test ===\n")

    logger = AgentLogger()
    llm_client = LLMClient(max_tokens_per_call=1500)
    diagnostic = DiagnosticAgent(llm_client=llm_client, logger=logger, max_tokens=1500)

    # Create alerts for a power outage
    alerts = [
        Alert(
            tower_id='tower_1',
            metric='status',
            value=-1,
            timestamp=time.time(),
            message='Tower tower_1 is completely DOWN.'
        ),
        Alert(
            tower_id='tower_1',
            metric='power_level',
            value=0.0,
            timestamp=time.time(),
            message="Metric 'power_level' out of range (0.0)."
        ),
        Alert(
            tower_id='tower_1',
            metric='signal_strength',
            value=-120.0,
            timestamp=time.time(),
            message="Metric 'signal_strength' out of range (-120.0)."
        ),
    ]

    print(f"1. Created {len(alerts)} alerts:")
    for a in alerts:
        print(f"   - {a.tower_id}: {a.message}")

    # Call diagnostic agent
    print("\n2. Calling diagnostic agent...")
    incident = diagnostic.diagnose_alerts(alerts)

    print(f"\n3. Result:")
    print(f"   Incident: {incident}")

    if incident:
        print(f"   Type: {incident.incident_type}")
        print(f"   Confidence: {incident.diagnosis_confidence}")
        print(f"   Root Cause: {incident.root_cause_hypothesis}")
        print(f"   Severity: {incident.severity}")
    else:
        print(f"   (No incident returned - diagnosis failed)")

    # Check logs
    print(f"\n4. Agent Logs ({len(logger.interactions)} total):")
    for log in logger.interactions:
        print(f"   Agent: {log['agent']}")
        print(f"   Tokens: {log['tokens']}")
        print(f"   Success: {log['success']}")
        print(f"   Tools: {log['tools_called']}")
        print(f"   Response preview: {log['response'][:200]}...")
        print()

    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    try:
        test_diagnostic()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
