#!/usr/bin/env python3
"""Check full diagnostic response for parsing."""

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
    logger = AgentLogger()
    llm_client = LLMClient(max_tokens_per_call=2000)
    diagnostic = DiagnosticAgent(llm_client=llm_client, logger=logger, max_tokens=2000)

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
    ]

    # Call diagnostic agent
    incident = diagnostic.diagnose_alerts(alerts)

    # Check full response from logs
    if logger.interactions:
        log = logger.interactions[0]
        print(f"Full response:\n{log['response']}\n")

        # Try to parse it
        response_text = log['response']
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        print(f"JSON start: {start}, end: {end}")
        if start != -1 and end > start:
            json_str = response_text[start:end]
            print(f"Extracted JSON:\n{json_str}\n")
            try:
                data = json.loads(json_str)
                print(f"Parsed JSON:\n{json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
        else:
            print("No valid JSON found in response")

if __name__ == "__main__":
    test_diagnostic()
