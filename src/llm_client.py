"""
LLM Client: Handles all communication with Claude AI, keeps track of how many tokens are used,
and parses Claude's responses including any tool calls it wants to make.
"""

from openai import OpenAI
import json
from typing import Optional, Any


class LLMClient:
    """Wrapper for OpenAI API (GPT-3.5-turbo) with token budget enforcement."""

    def __init__(self, model: str = "gpt-3.5-turbo", max_tokens_per_call: int = 400):
        self.client = OpenAI()  # Uses OPENAI_API_KEY env var
        self.model = model
        self.max_tokens_per_call = max_tokens_per_call
        self.total_tokens_used = 0
        self.calls_made = 0

    def reset_token_count(self):
        """Reset token counter for new incident."""
        self.total_tokens_used = 0
        self.calls_made = 0

    def _convert_tools_schema(self, tools: Optional[list]) -> Optional[list]:
        """Convert Claude tool schema to OpenAI function schema."""
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def call(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        max_retries: int = 3
    ) -> dict:
        """
        Call OpenAI API with optional function calling.

        Returns: {
            'content': str,  # Response text
            'tokens_in': int,
            'tokens_out': int,
            'total_tokens': int,
            'stop_reason': str,
            'tool_calls': list  # If tools were called
        }
        """
        self.calls_made += 1

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        openai_tools = self._convert_tools_schema(tools) if tools else None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens_per_call,
                tools=openai_tools,
                tool_choice="auto" if openai_tools else None,
                temperature=0.7
            )

            # Extract tokens
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            total = tokens_in + tokens_out
            self.total_tokens_used += total

            # Process response
            tool_calls = []
            response_text = ""

            for choice in response.choices:
                if choice.message.content:
                    response_text += choice.message.content

                # Check for function calls
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        tool_calls.append({
                            'id': tool_call.id,
                            'name': tool_call.function.name,
                            'input': json.loads(tool_call.function.arguments)
                        })

            return {
                'content': response_text,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'total_tokens': total,
                'stop_reason': response.choices[0].finish_reason if response.choices else 'unknown',
                'tool_calls': tool_calls
            }

        except Exception as e:
            return {
                'error': str(e),
                'content': '',
                'tokens_in': 0,
                'tokens_out': 0,
                'total_tokens': 0,
                'stop_reason': 'error',
                'tool_calls': []
            }

    def call_with_tool_results(
        self,
        system_prompt: str,
        messages: list,
        tools: Optional[list] = None
    ) -> dict:
        """
        Continue conversation after tool execution.
        messages format: [{'role': 'user|assistant', 'content': ...}, ...]
        System prompt is prepended to messages list.
        """
        # OpenAI requires system prompt as first message in array
        openai_tools = self._convert_tools_schema(tools) if tools else None

        # Prepend system message to messages
        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + messages

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_system,
                max_tokens=self.max_tokens_per_call,
                tools=openai_tools,
                tool_choice="auto" if openai_tools else None,
                temperature=0.7
            )

            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            total = tokens_in + tokens_out
            self.total_tokens_used += total

            tool_calls = []
            response_text = ""

            for choice in response.choices:
                if choice.message.content:
                    response_text += choice.message.content

                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        tool_calls.append({
                            'id': tool_call.id,
                            'name': tool_call.function.name,
                            'input': json.loads(tool_call.function.arguments)
                        })

            return {
                'content': response_text,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'total_tokens': total,
                'stop_reason': response.choices[0].finish_reason if response.choices else 'unknown',
                'tool_calls': tool_calls
            }

        except Exception as e:
            return {
                'error': str(e),
                'content': '',
                'tokens_in': 0,
                'tokens_out': 0,
                'total_tokens': 0,
                'stop_reason': 'error',
                'tool_calls': []
            }

    def get_token_usage_summary(self) -> dict:
        """Get token usage stats."""
        return {
            'total_tokens': self.total_tokens_used,
            'calls_made': self.calls_made,
            'avg_tokens_per_call': (
                self.total_tokens_used / self.calls_made if self.calls_made > 0 else 0
            )
        }
