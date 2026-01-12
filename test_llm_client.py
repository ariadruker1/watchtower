#!/usr/bin/env python3
"""Test LLM client directly to debug tool calling."""

import json
from dotenv import load_dotenv

load_dotenv()

from src.llm_client import LLMClient
from src.agents.tools import TOOLS_SCHEMA

def test_llm_client():
    """Test OpenAI API tool calling directly."""
    print("\n=== LLM Client Test ===\n")

    client = LLMClient(model="gpt-3.5-turbo", max_tokens_per_call=1500)

    # Create a simple test prompt
    system_prompt = "You are a test agent. Call the get_weather_at_tower tool for tower_1."
    user_message = "Call the weather tool for tower_1 and respond with JSON: {\"status\": \"ok\", \"result\": \"...\"}. After calling the tool, respond again with final JSON."

    print("1. Initial request with tool availability...")
    print(f"   System: {system_prompt}")
    print(f"   User: {user_message[:100]}...\n")

    response = client.call(
        system_prompt=system_prompt,
        user_message=user_message,
        tools=TOOLS_SCHEMA
    )

    print(f"   Response status: {response.get('stop_reason')}")
    print(f"   Content: {response.get('content', '')[:150]}")
    print(f"   Tool calls: {[tc['name'] for tc in response.get('tool_calls', [])]}")
    print(f"   Tokens: {response.get('total_tokens')}")

    # If tool calls were made, follow up
    if response.get('tool_calls'):
        print("\n2. Tool execution...")
        tool_calls = response.get('tool_calls', [])
        from src.agents.tools import execute_tool

        # Build messages for continuation
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response.get('content', ''), "tool_calls": [
                {"id": tc['id'], "type": "function", "function": {"name": tc['name'], "arguments": json.dumps(tc['input'])}}
                for tc in tool_calls
            ]}
        ]

        print(f"   Executing {len(tool_calls)} tool(s)...")
        for tool_call in tool_calls:
            tool_result = execute_tool(tool_call['name'], tool_call['input'])
            print(f"     - {tool_call['name']}: {str(tool_result)[:100]}...")
            messages.append({
                'role': 'tool',
                'tool_call_id': tool_call['id'],
                'name': tool_call['name'],
                'content': json.dumps(tool_result)
            })

        print("\n3. Follow-up request after tool execution...")
        response2 = client.call_with_tool_results(
            system_prompt=system_prompt,
            messages=messages,
            tools=TOOLS_SCHEMA
        )

        print(f"   Response status: {response2.get('stop_reason')}")
        print(f"   Content: {response2.get('content', '')[:200]}")
        print(f"   Tool calls: {[tc['name'] for tc in response2.get('tool_calls', [])]}")
        print(f"   Tokens: {response2.get('total_tokens')}")

        if not response2.get('content'):
            print("\n   WARNING: Empty response after tool execution!")
            print(f"   Full response2: {response2}")

    print(f"\n4. Total tokens used: {client.total_tokens_used}")
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    try:
        test_llm_client()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
