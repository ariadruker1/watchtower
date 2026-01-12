"""Remediation Agent: AI-powered solution planning for network incidents."""

import json
from typing import Optional
from src.data_models import Incident, RemediationPlan, RemediationAction
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from src.agents.tools import TOOLS_SCHEMA, execute_tool


class RemediationAgent:
    """Pragmatic planner that creates safe, effective remediation strategies."""

    def __init__(self, llm_client: Optional[LLMClient] = None, logger: Optional[AgentLogger] = None, max_tokens: int = 400):
        self.llm_client = llm_client or LLMClient(max_tokens_per_call=max_tokens)
        self.logger = logger
        self.max_tokens = max_tokens

    def create_plan(self, incident: Incident, feedback: str = "") -> Optional[RemediationPlan]:
        """Create a remediation plan using Claude with tool access."""
        if not incident:
            return None

        # Build system prompt with persona
        system_prompt = """You are a pragmatic operations lead. Create a safe, efficient remediation plan.
Consult runbooks and engineer availability. Consider risk levels and customer impact.
Return JSON with: actions (list), rollback_plan, verification_steps, plan_confidence (0.0-1.0), risk_assessment."""

        # Build user message
        user_message = f"""Create a remediation plan for this incident:
Type: {incident.incident_type}
Root Cause: {incident.root_cause_hypothesis}
Affected Sites: {', '.join(incident.affected_cell_ids)}
Diagnosis Confidence: {incident.diagnosis_confidence}

{f"Feedback: {feedback}" if feedback else ""}

Call tools to get runbook and engineer availability. Then respond with JSON:
{{"actions": ["action1", "action2"], "rollback_plan": "...", "verification_steps": ["step1"], "plan_confidence": 0.0-1.0, "risk_assessment": "..."}}"""

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

        # Process tool calls if any
        tool_calls_made = []
        messages = [{"role": "user", "content": user_message}]

        if response.get('tool_calls'):
            tool_calls = response.get('tool_calls', [])
            tool_calls_made = [tc['name'] for tc in tool_calls]

            # Execute tools
            tool_results = []
            for tool_call in tool_calls:
                tool_result = execute_tool(tool_call['name'], tool_call['input'])
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_call['id'],
                    'content': json.dumps(tool_result)
                })

            # Continue conversation
            messages.append({'role': 'assistant', 'content': [
                {'type': 'tool_use', 'id': tc['id'], 'name': tc['name'], 'input': tc['input']}
                for tc in tool_calls
            ]})
            messages.append({'role': 'user', 'content': tool_results})

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
                'RemediationAgent', user_message[:150], str(final_response)[:150],
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
                rollback_plan=plan_data.get('rollback_plan', 'Manual rollback required'),
                verification_steps=plan_data.get('verification_steps', []),
                plan_confidence=min(max(plan_data.get('plan_confidence', incident.diagnosis_confidence), 0), 1.0)
            )

            return plan

        except (json.JSONDecodeError, KeyError, TypeError):
            return None