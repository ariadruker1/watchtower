"""
Agent Logger: Records what each agent thinks and does so we can see the full story of how a problem was diagnosed and fixed,
and audit all the decisions made along the way.
"""

from typing import Optional, List
from datetime import datetime
import json
import re


class AgentLogger:
    """Log all agent prompts, responses, and tool calls."""

    def __init__(self):
        self.interactions: List[dict] = []
        self.current_incident_logs: List[dict] = []

    def _extract_json_from_response(self, response: str) -> Optional[dict]:
        """Extract JSON object from response string."""
        try:
            if isinstance(response, str):
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def _generate_natural_language_log(self, agent_name: str, prompt: str, response: str, tools_called: List[str], tokens_used: int) -> str:
        """Generate a 3-stage natural language log entry with actual extracted data."""

        # Extract JSON response for parsing
        response_json = self._extract_json_from_response(response)

        # Stage 1: Received - what was the agent notified about
        received = ""
        if agent_name == 'DiagnosticAgent':
            received = "Cell tower network alert detected with anomalies requiring analysis."
        elif agent_name == 'RemediationAgent':
            received = "Incident diagnosis complete. Developing remediation strategy for affected sites."
        elif agent_name == 'GovernanceAgent':
            received = "Remediation plan generated. Validating against company policies and legal requirements."
        else:
            received = "Request received for incident processing."

        # Stage 2: Investigated - what did the agent analyze
        if agent_name == 'DiagnosticAgent':
            investigated = "Weather conditions, maintenance history, network metrics, and signal patterns"
        elif agent_name == 'RemediationAgent':
            investigated = "Available runbooks, engineer schedules, risk factors, and solution feasibility"
        elif agent_name == 'GovernanceAgent':
            investigated = "Company policies, legal/regulatory requirements, data protection obligations, and incident severity"
        else:
            investigated = "Incident data and process requirements"

        if tools_called:
            investigated += f" using {', '.join(tools_called)}"

        # Stage 3: Suggestions - what does the agent recommend (extracted from actual response)
        suggestions = ""
        if agent_name == 'DiagnosticAgent' and response_json:
            # Extract diagnosis information
            root_cause = response_json.get('root_cause_hypothesis', 'Analysis incomplete')
            confidence = response_json.get('diagnosis_confidence', 0)
            suggestions = f"{root_cause}\nDiagnosis Confidence: {confidence:.2f}"

        elif agent_name == 'RemediationAgent' and response_json:
            # Extract proposed actions and preventative measures
            actions = response_json.get('actions', [])
            measures = response_json.get('future_preventative_measures', [])

            if actions:
                suggestions = "Proposed Actions:\n"
                for action in actions[:3]:  # Show up to 3 actions
                    suggestions += f"- {action}\n"
                suggestions = suggestions.rstrip()

            if measures:
                suggestions += "\nFuture Preventative Measures:\n"
                for measure in measures[:2]:  # Show up to 2 measures
                    suggestions += f"- {measure}\n"
                suggestions = suggestions.rstrip()

            if not actions and not measures:
                suggestions = "Plan generation in progress."

        elif agent_name == 'GovernanceAgent' and response_json:
            # Extract policy review decision
            decision = response_json.get('decision', 'PENDING')
            reason = response_json.get('reason', 'Review in progress')

            if 'APPROVE' in decision:
                suggestions = f"Policy Review: APPROVED. {reason}"
            elif 'REJECT' in decision:
                suggestions = f"Policy Review: REJECTED. {reason}"
            else:
                suggestions = f"Policy Review: {decision}. {reason}"

        else:
            suggestions = "Processing complete."

        # Combine all stages with clear section headers
        natural_language_log = (
            f"Received: {received}\n"
            f"Investigated: {investigated}\n"
            f"Suggestions: {suggestions}"
        )
        return natural_language_log

    def log_interaction(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        tools_called: List[str],
        tokens_used: int,
        success: bool = True
    ):
        """Log an agent interaction with natural language formatting."""
        # Generate natural language log (pass full response for extraction)
        natural_language_log = self._generate_natural_language_log(agent_name, prompt, response, tools_called, tokens_used)

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'prompt': prompt[:200] + '...' if len(prompt) > 200 else prompt,  # Truncate for display
            'response': response,  # Keep full response for extraction
            'tools_called': tools_called,
            'tokens': tokens_used,
            'success': success,
            'natural_language_log': natural_language_log,  # Full natural language version with 3 stages
            'full_log_history': natural_language_log  # Also store in full_log_history field
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
