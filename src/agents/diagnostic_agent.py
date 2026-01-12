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
        system_prompt = """You are a veteran field engineer with deep expertise in telecom network infrastructure.
Analyze the alerts, use the available tools to gather evidence about:
1. Physical causes (weather, maintenance, regional events)
2. Known telecom patterns that match these symptoms
3. Historical context

Return JSON with: incident_type, root_cause_hypothesis, diagnosis_confidence (0.0-1.0), evidence_summary."""

        # Build user message
        user_message = f"""Analyze these alerts and diagnose the root cause:
{alert_text}

{f"Previous feedback: {feedback}" if feedback else ""}

Call tools to investigate. Then respond with JSON in format:
{{"incident_type": "POWER_OUTAGE|FIBER_CUT|SIGNAL_INTERFERENCE|OTHER", "root_cause_hypothesis": "...", "diagnosis_confidence": 0.0-1.0, "evidence_summary": "..."}}"""

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

        # Process tool calls
        messages = [{"role": "user", "content": user_message}]
        assistant_content = []
        tool_calls_made = []

        # First response might have tool calls
        for block in (response.get('content') if isinstance(response['content'], list) else [response.get('content')]):
            if hasattr(block, 'type') and block.type == 'tool_use':
                assistant_content.append(block)
                tool_calls_made.append(block.name)
            elif isinstance(block, dict) and block.get('type') == 'tool_use':
                assistant_content.append(block)
                tool_calls_made.append(block.get('name'))

        # If tools were called, execute them and continue conversation
        if tool_calls_made or response.get('tool_calls'):
            tool_calls = response.get('tool_calls', [])
            tool_calls_made = [tc['name'] for tc in tool_calls]

            # Build tool results
            tool_results = []
            for tool_call in tool_calls:
                tool_result = execute_tool(tool_call['name'], tool_call['input'])
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_call['id'],
                    'content': json.dumps(tool_result)
                })

            # Continue conversation with tool results
            messages.append({'role': 'assistant', 'content': [
                {'type': 'tool_use', 'id': tc['id'], 'name': tc['name'], 'input': tc['input']}
                for tc in tool_calls
            ]})
            messages.append({'role': 'user', 'content': tool_results})

            # Get final diagnosis
            response2 = self.llm_client.call_with_tool_results(
                system_prompt=system_prompt,
                messages=messages,
                tools=TOOLS_SCHEMA
            )

            final_response = response2.get('content', '')
            total_tokens = response.get('total_tokens', 0) + response2.get('total_tokens', 0)
        else:
            final_response = response.get('content', '')
            total_tokens = response.get('total_tokens', 0)

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