"""Claude API wrapper with tool_use support and token tracking."""

import anthropic
import json
from typing import Optional, Any


class LLMClient:
    """Wrapper for Claude API with token budget enforcement."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", max_tokens_per_call: int = 400):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens_per_call = max_tokens_per_call
        self.total_tokens_used = 0
        self.calls_made = 0

    def reset_token_count(self):
        """Reset token counter for new incident."""
        self.total_tokens_used = 0
        self.calls_made = 0

    def call(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        max_retries: int = 3
    ) -> dict:
        """
        Call Claude API with optional tools.

        Returns: {
            'content': str or list,  # Response text or tool_use blocks
            'tokens_in': int,
            'tokens_out': int,
            'total_tokens': int,
            'stop_reason': str,
            'tool_calls': list  # If tools were called
        }
        """
        self.calls_made += 1

        messages = [{"role": "user", "content": user_message}]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_per_call,
                system=system_prompt,
                tools=tools if tools else None,
                messages=messages
            )

            # Extract tokens
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            total = tokens_in + tokens_out
            self.total_tokens_used += total

            # Process response content
            tool_calls = []
            response_text = ""

            for block in response.content:
                if block.type == "text":
                    response_text += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        'id': block.id,
                        'name': block.name,
                        'input': block.input
                    })

            return {
                'content': response_text or response.content,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'total_tokens': total,
                'stop_reason': response.stop_reason,
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
        messages: list,  # Full conversation history
        tools: Optional[list] = None
    ) -> dict:
        """
        Continue conversation after tool execution.
        messages format: [{'role': 'user|assistant', 'content': ...}, ...]
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_per_call,
                system=system_prompt,
                tools=tools if tools else None,
                messages=messages
            )

            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            total = tokens_in + tokens_out
            self.total_tokens_used += total

            tool_calls = []
            response_text = ""

            for block in response.content:
                if block.type == "text":
                    response_text += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        'id': block.id,
                        'name': block.name,
                        'input': block.input
                    })

            return {
                'content': response_text or response.content,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'total_tokens': total,
                'stop_reason': response.stop_reason,
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
