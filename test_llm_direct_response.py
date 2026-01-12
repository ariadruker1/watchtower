#!/usr/bin/env python3
"""Test LLM response directly without logging."""

import json
from dotenv import load_dotenv

load_dotenv()

from src.llm_client import LLMClient
from src.agents.tools import TOOLS_SCHEMA, execute_tool
import time

def test():
    """Test LLM response."""
    llm_client = LLMClient(max_tokens_per_call=2000)

    # System and user messages matching diagnostic agent
    system_prompt = """You are a veteran field engineer. Your ONLY job is to diagnose incidents.
CRITICAL: Respond with ONLY a JSON object (no text before or after).
Use tools to investigate, then output JSON with exactly these fields:
- incident_type: POWER_OUTAGE|FIBER_CUT|SIGNAL_INTERFERENCE|OTHER
- root_cause_hypothesis: Brief cause description
- diagnosis_confidence: 0.0-1.0
- evidence_summary: Evidence from tools
NO PROSE. ONLY JSON."""

    user_message = """Diagnose this network incident:
- tower_1: status=-1 (message: Tower tower_1 is completely DOWN.)
- tower_1: power_level=0.0 (message: Metric 'power_level' out of range (0.0).)

Use tools, then respond with ONLY this JSON format (no prose):
{"incident_type": "POWER_OUTAGE|FIBER_CUT|SIGNAL_INTERFERENCE|OTHER", "root_cause_hypothesis": "description", "diagnosis_confidence": 0.85, "evidence_summary": "summary"}

ONLY JSON. NO OTHER TEXT."""

    # First call with tools
    response = llm_client.call(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=TOOLS_SCHEMA
    )

    print(f"First response stop_reason: {response.get('stop_reason')}")
    print(f"First response has {len(response.get('tool_calls', []))} tool calls")

    if response.get('tool_calls'):
        # Build message format and execute tools
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response.get('content', ''), "tool_calls": [
                {"id": tc['id'], "type": "function", "function": {"name": tc['name'], "arguments": json.dumps(tc['input'])}}
                for tc in response.get('tool_calls', [])
            ]}
        ]

        for tool_call in response.get('tool_calls', []):
            tool_result = execute_tool(tool_call['name'], tool_call['input'])
            messages.append({
                'role': 'tool',
                'tool_call_id': tool_call['id'],
                'name': tool_call['name'],
                'content': json.dumps(tool_result)
            })

        # Follow-up call
        response2 = llm_client.call_with_tool_results(
            system_prompt=system_prompt,
            messages=messages,
            tools=TOOLS_SCHEMA
        )

        print(f"\nSecond response stop_reason: {response2.get('stop_reason')}")
        print(f"Second response length: {len(response2.get('content', ''))}")
        print(f"\nFull second response:")
        print(response2.get('content', ''))

        # Try to parse JSON
        print("\nJSON parsing:")
        content = response2.get('content', '')
        start = content.find('{')
        end = content.rfind('}') + 1

        if start != -1 and end > start:
            json_str = content[start:end]
            try:
                data = json.loads(json_str)
                print(f"Success! Parsed JSON:")
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Attempted JSON:\n{json_str}")
        else:
            print("No JSON found")

if __name__ == "__main__":
    test()
