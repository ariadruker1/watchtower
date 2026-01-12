"""Diagnostic Agent: AI-powered root cause analysis for network incidents."""

import json
from typing import Optional, List
from src.data_models import Alert, Incident
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from src.agents.tools import TOOLS_SCHEMA, execute_tool


class DiagnosticAgent:
    """Field engineer that diagnoses network incidents using Claude AI and evidence gathering."""

    def __init__(self, llm_client: Optional[LLMClient] = None, logger: Optional[AgentLogger] = None, max_tokens: int = 400):
        self.llm_client = llm_client or LLMClient(max_tokens_per_call=max_tokens)
        self.logger = logger
        self.max_tokens = max_tokens

    def diagnose_alerts(self, alerts: List[Alert], feedback: str = "") -> Optional[Incident]:
        """Diagnose root cause of alerts using Claude with tool_use."""
        if not alerts:
            return None

        # Format alerts for prompt
        alert_text = "\n".join([
            f"- {a.tower_id}: {a.metric}={a.value} (message: {a.message})"
            for a in alerts
        ])

        # Build system prompt with persona
        system_prompt = """You are a veteran field engineer. Your ONLY job is to diagnose incidents.
CRITICAL: Respond with ONLY a JSON object (no text before or after).
Use tools to investigate, then output JSON with exactly these fields:
- incident_type: POWER_OUTAGE|FIBER_CUT|SIGNAL_INTERFERENCE|OTHER
- root_cause_hypothesis: Brief cause description
- diagnosis_confidence: 0.0-1.0
- evidence_summary: Evidence from tools
NO PROSE. ONLY JSON."""

        # Build user message
        user_message = f"""Diagnose this network incident:
{alert_text}

{f"Feedback: {feedback}" if feedback else ""}

Use tools, then respond with ONLY this JSON format (no prose):
{{"incident_type": "POWER_OUTAGE|FIBER_CUT|SIGNAL_INTERFERENCE|OTHER", "root_cause_hypothesis": "description", "diagnosis_confidence": 0.85, "evidence_summary": "summary"}}

ONLY JSON. NO OTHER TEXT."""

        # Call Claude with tools
        response = self.llm_client.call(
            system_prompt=system_prompt,
            user_message=user_message,
            tools=TOOLS_SCHEMA
        )

        if response.get('error'):
            if self.logger:
                self.logger.log_interaction(
                    'DiagnosticAgent', user_message, f"Error: {response['error']}",
                    [], 0, False
                )
            return None

        # Get tool calls from OpenAI response and handle multiple rounds
        tool_calls_made = []
        total_tokens = response.get('total_tokens', 0)

        if response.get('tool_calls'):
            # Build initial message with first batch of tool calls
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response.get('content', ''), "tool_calls": [
                    {"id": tc['id'], "type": "function", "function": {"name": tc['name'], "arguments": json.dumps(tc['input'])}}
                    for tc in response.get('tool_calls', [])
                ]}
            ]

            # Multi-round tool handling: keep calling LLM until it stops asking for tools
            current_response = response
            max_tool_rounds = 3  # Prevent infinite loops
            round_count = 0

            while current_response.get('tool_calls') and round_count < max_tool_rounds:
                round_count += 1
                tool_calls = current_response.get('tool_calls', [])
                tool_calls_made.extend([tc['name'] for tc in tool_calls])

                # Execute all tool calls in this round
                for tool_call in tool_calls:
                    tool_result = execute_tool(tool_call['name'], tool_call['input'])
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call['id'],
                        'name': tool_call['name'],
                        'content': json.dumps(tool_result)
                    })

                # Get next response after tools
                current_response = self.llm_client.call_with_tool_results(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=TOOLS_SCHEMA
                )
                total_tokens += current_response.get('total_tokens', 0)

                # If this response has tool calls, add it to messages for next round
                if current_response.get('tool_calls'):
                    messages.append({
                        "role": "assistant",
                        "content": current_response.get('content', ''),
                        "tool_calls": [
                            {"id": tc['id'], "type": "function", "function": {"name": tc['name'], "arguments": json.dumps(tc['input'])}}
                            for tc in current_response.get('tool_calls', [])
                        ]
                    })

            final_response = current_response.get('content', '')
        else:
            final_response = response.get('content', '')

        # Log interaction
        if self.logger:
            self.logger.log_interaction(
                'DiagnosticAgent', user_message[:150], str(final_response)[:150],
                tool_calls_made, total_tokens, True
            )

        # Parse JSON response
        try:
            # Extract JSON from response
            if isinstance(final_response, str):
                start = final_response.find('{')
                end = final_response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = final_response[start:end]
                    diagnosis = json.loads(json_str)
                else:
                    return None
            else:
                return None

            # Create Incident object
            incident = Incident(
                incident_type=diagnosis.get('incident_type', 'UNKNOWN'),
                severity=self._confidence_to_severity(diagnosis.get('diagnosis_confidence', 0)),
                affected_cell_ids=[a.tower_id for a in alerts],
                root_cause_hypothesis=diagnosis.get('root_cause_hypothesis', ''),
                evidence={'summary': diagnosis.get('evidence_summary', '')},
                diagnosis_confidence=min(max(diagnosis.get('diagnosis_confidence', 0.5), 0), 1.0)
            )
            return incident

        except (json.JSONDecodeError, KeyError):
            return None

    def _confidence_to_severity(self, confidence: float) -> str:
        """Map confidence to severity level."""
        if confidence >= 0.9:
            return 'CRITICAL'
        elif confidence >= 0.7:
            return 'HIGH'
        else:
            return 'MEDIUM'