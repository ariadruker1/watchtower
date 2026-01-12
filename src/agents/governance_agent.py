"""
Governance Agent: Reviews the remediation plan against company policies and legal requirements,
then either approves it or rejects it with reasons so it can be improved before human review.
"""

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
        system_prompt = """You are a pragmatic compliance officer. Your job is to approve reasonable remediation plans while ensuring basic safety and legal requirements.
CRITICAL: Respond with ONLY a JSON object (no text before or after).
Favor APPROVAL for reasonable plans that address the incident. Only reject if there are serious safety or legal violations.
Return JSON with exactly these fields:
- decision: APPROVE, REJECT_LOW_CONFIDENCE, REJECT_BAD_PLAN, or REJECT_POLICY_VIOLATION
- reason_code: Code for decision
- reason: Brief explanation
- policies_checked: Array of policy names checked
- legal_requirements_reviewed: Array of legal/regulatory requirements reviewed
NO PROSE. ONLY JSON."""

        # Build user message
        user_message = f"""Review this incident and remediation plan. APPROVE if the plan is reasonable and addresses the incident.

Incident: {incident.incident_type}
  Confidence: {incident.diagnosis_confidence}
  Severity: {incident.severity}

{f"Plan: {str(plan.to_dict())[:200]}" if plan else "No plan"}

Quickly verify:
1. Plan addresses the incident type
2. No obvious safety violations
3. Plan is feasible

Respond with ONLY this JSON format (no prose):
{{"decision": "APPROVE|REJECT_LOW_CONFIDENCE|REJECT_BAD_PLAN|REJECT_POLICY_VIOLATION", "reason_code": "code", "reason": "reason", "policies_checked": ["policy1"], "legal_requirements_reviewed": ["requirement1"]}}

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

        # Log interaction - pass full response for extraction
        if self.logger:
            self.logger.log_interaction(
                'GovernanceAgent', user_message[:150], str(final_response),
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
                policies_checked=decision_data.get('policies_checked', []),
                legal_requirements_reviewed=decision_data.get('legal_requirements_reviewed', [])
            )

            return decision

        except (json.JSONDecodeError, KeyError, TypeError):
            return GovernanceDecision(
                decision='REJECT',
                reason_code='PARSE_ERROR',
                reason='Error parsing governance response',
                policies_checked=[]
            )