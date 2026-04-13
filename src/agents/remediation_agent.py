"""
Remediation Agent: Takes the diagnosis and creates a detailed action plan including specific steps to fix it,
preventative measures to stop it happening again, and verification steps to confirm it's fixed.
"""

import json
from typing import Optional
from src.data_models import Incident, RemediationPlan, RemediationAction
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from src.agents.tools import TOOLS_SCHEMA, execute_tool


class RemediationAgent:
    """Pragmatic planner that creates safe, effective remediation strategies."""

    def __init__(self, llm_client: Optional[LLMClient] = None, logger: Optional[AgentLogger] = None, max_tokens: int = 1500):
        self.llm_client = llm_client or LLMClient(max_tokens_per_call=max_tokens)
        self.logger = logger
        self.max_tokens = max_tokens

    def create_plan(self, incident: Incident, feedback: str = "") -> Optional[RemediationPlan]:
        """Create a remediation plan using Claude with tool access."""
        if not incident:
            return None

        # Build system prompt with persona
        system_prompt = """You are a pragmatic operations lead. Your ONLY job is to create remediation plans.
CRITICAL: Respond with ONLY a JSON object (no text before or after).
Use tools to get runbook and engineer schedule, then output JSON with exactly these fields:
- actions: Array of action strings describing immediate remediation steps. Use V### format for vehicles (e.g., V001, V002), not T### format.
- future_preventative_measures: Array of preventative measures to reduce likelihood of recurrence
- verification_steps: Array of verification step strings
- plan_confidence: 0.0-1.0
- risk_assessment: Risk assessment string
NO PROSE. ONLY JSON."""

        # Build user message
        user_message = f"""Create a remediation plan for this incident:
Type: {incident.incident_type}
Root Cause: {incident.root_cause_hypothesis}
Affected Sites: {', '.join(incident.affected_cell_ids)}
Diagnosis Confidence: {incident.diagnosis_confidence}

{f"Feedback: {feedback}" if feedback else ""}

Use tools to get runbook and engineer availability, then respond with ONLY this JSON format (no prose):
{{"actions": ["action1 using V001", "action2"], "future_preventative_measures": ["measure1", "measure2"], "verification_steps": ["step1", "step2"], "plan_confidence": 0.85, "risk_assessment": "assessment"}}

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
                    'RemediationAgent', user_message, f"Error: {response['error']}",
                    [], 0, False
                )
            return None

        # Process tool calls if any - handle multiple rounds
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

            # Multi-round tool handling
            current_response = response
            max_tool_rounds = 3
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

                # Get next response
                current_response = self.llm_client.call_with_tool_results(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=TOOLS_SCHEMA
                )
                total_tokens += current_response.get('total_tokens', 0)

                # If more tools needed, add to messages
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

        # Log interaction - pass full response for extraction
        if self.logger:
            self.logger.log_interaction(
                'RemediationAgent', user_message[:150], str(final_response),
                tool_calls_made, total_tokens, True
            )

        # Parse JSON response
        try:
            if isinstance(final_response, str):
                start = final_response.find('{')
                end = final_response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = final_response[start:end]
                    plan_data = json.loads(json_str)
                else:
                    return None
            else:
                return None

            # Create RemediationAction objects from actions list
            actions = []
            action_list = plan_data.get('actions', [])
            for i, action_desc in enumerate(action_list):
                actions.append(RemediationAction(
                    action_type=f"{incident.incident_type}_action_{i}",
                    description=action_desc,
                    before_state={'incident': incident.to_dict()},
                    after_state_expected={},
                    execution_steps=[action_desc]
                ))

            # Create RemediationPlan
            plan = RemediationPlan(
                incident_id=incident.incident_id,
                actions=actions if actions else [RemediationAction(
                    action_type=incident.incident_type,
                    description="Pending manual review",
                    before_state={},
                    after_state_expected={},
                    execution_steps=[]
                )],
                rollback_plan=plan_data.get('risk_assessment', 'No rollback plan specified'),
                verification_steps=plan_data.get('verification_steps', []),
                plan_confidence=min(max(plan_data.get('plan_confidence', incident.diagnosis_confidence), 0), 1.0)
            )

            return plan

        except (json.JSONDecodeError, KeyError, TypeError):
            return None