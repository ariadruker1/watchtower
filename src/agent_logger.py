"""Centralized logging for agent interactions with LLM."""

from typing import Optional, List
from datetime import datetime


class AgentLogger:
    """Log all agent prompts, responses, and tool calls."""

    def __init__(self):
        self.interactions: List[dict] = []
        self.current_incident_logs: List[dict] = []

    def log_interaction(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tools_called: List[str],
        tokens_used: int,
        success: bool = True
    ):
        """Log an agent interaction."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'prompt': prompt[:200] + '...' if len(prompt) > 200 else prompt,  # Truncate for display
            'response': response[:1000] + '...' if len(response) > 1000 else response,
            'tools_called': tools_called,
            'tokens': tokens_used,
            'success': success
        }
        self.interactions.append(log_entry)
        self.current_incident_logs.append(log_entry)

    def clear_incident_logs(self):
        """Clear logs for current incident."""
        self.current_incident_logs = []

    def get_incident_logs(self) -> List[dict]:
        """Get logs for current incident."""
        return self.current_incident_logs

    def format_logs_for_ui(self, max_lines: int = 20) -> List[str]:
        """Format logs for display in UI."""
        lines = []
        for log in self.current_incident_logs[-max_lines:]:
            line = (
                f"[{log['agent']}] "
                f"Tokens: {log['tokens']} | "
                f"Tools: {', '.join(log['tools_called']) if log['tools_called'] else 'none'} | "
                f"Success: {log['success']}"
            )
            lines.append(line)
        return lines

    def get_total_tokens(self) -> int:
        """Get total tokens used in current incident."""
        return sum(log['tokens'] for log in self.current_incident_logs)

    def get_all_interactions(self) -> List[dict]:
        """Get all logged interactions."""
        return self.interactions
