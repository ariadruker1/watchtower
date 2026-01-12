"""Governance Agent: Policy compliance validation for incidents and remediation plans."""

import json
from typing import Optional
from src.data_models import Incident, RemediationPlan, GovernanceDecision
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from src.agents.tools import TOOLS_SCHEMA, execute_tool


class GovernanceAgent:
    """Meticulous auditor that ensures compliance with safety and policy requirements."""

    def __init__(self, llm_client: Optional[LLMClient] = None, logger: Optional[AgentLogger] = None, max_tokens: int = 1000):
        self.llm_client = llm_client or LLMClient(max_tokens_per_call=max_tokens)
        self.logger = logger
        self.max_tokens = max_tokens

    def evaluate(self, incident: Incident, plan: Optional[RemediationPlan] = None) -> GovernanceDecision:
        """Evaluate incident and plan against company policies."""
        if not incident:
            return GovernanceDecision(
                decision='REJECT',
                reason_code='INVALID_INCIDENT',
                reason='No incident data provided',
                policies_checked=['basic_validation']
            )

        # Build system prompt with persona
        system_prompt = """You are a meticulous compliance auditor. Your ONLY job is to validate policies.
CRITICAL: Respond with ONLY a JSON object (no text before or after).
Check policies and return JSON with exactly these fields:
- decision: APPROVE, REJECT_LOW_CONFIDENCE, REJECT_BAD_PLAN, or REJECT_POLICY_VIOLATION
- reason_code: Code for decision
- reason: Brief explanation
- policies_checked: Array of policy names checked
NO PROSE. ONLY JSON."""

        # Build user message
        user_message = f"""Review this incident and remediation plan for policy compliance:

Incident: {incident.incident_type}
  Confidence: {incident.diagnosis_confidence}
  Severity: {incident.severity}

{f"Plan: {str(plan.to_dict())[:200]}" if plan else "No plan"}

Use policy tools if needed, then respond with ONLY this JSON format (no prose):
{{"decision": "APPROVE|REJECT_LOW_CONFIDENCE|REJECT_BAD_PLAN|REJECT_POLICY_VIOLATION", "reason_code": "code", "reason": "reason", "policies_checked": ["policy1"]}}

ONLY JSON. NO OTHER TEXT."""

        # Call Claude
        response = self.llm_client.call(
            system_prompt=system_prompt,
            user_message=user_message,
            tools=TOOLS_SCHEMA
        )

        if response.get('error'):
            if self.logger:
                self.logger.log_interaction(
                    'GovernanceAgent', user_message, f"Error: {response['error']}",
                    [], 0, False
                )
            return GovernanceDecision(
                decision='REJECT',
                reason_code='LLM_ERROR',
                reason=f"Error: {response['error']}",
                policies_checked=['error_handling']
            )

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

        # Log interaction
        if self.logger:
            self.logger.log_interaction(
                'GovernanceAgent', user_message[:150], str(final_response)[:150],
                tool_calls_made, total_tokens, True
            )

        # Parse JSON response
        try:
            if isinstance(final_response, str):
                start = final_response.find('{')
                end = final_response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = final_response[start:end]
                    decision_data = json.loads(json_str)
                else:
                    return GovernanceDecision(
                        decision='REJECT',
                        reason_code='PARSE_ERROR',
                        reason='Could not parse governance decision',
                        policies_checked=[]
                    )
            else:
                return GovernanceDecision(
                    decision='REJECT',
                    reason_code='INVALID_RESPONSE',
                    reason='Invalid response from governance evaluation',
                    policies_checked=[]
                )

            # Create GovernanceDecision
            decision = GovernanceDecision(
                decision=decision_data.get('decision', 'REJECT'),
                reason_code=decision_data.get('reason_code', 'UNKNOWN'),
                reason=decision_data.get('reason', 'Policy violation'),
                policies_checked=decision_data.get('policies_checked', [])
            )

            return decision

        except (json.JSONDecodeError, KeyError, TypeError):
            return GovernanceDecision(
                decision='REJECT',
                reason_code='PARSE_ERROR',
                reason='Error parsing governance response',
                policies_checked=[]
            )