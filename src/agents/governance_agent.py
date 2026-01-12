"""Governance Agent: Policy compliance validation for incidents and remediation plans."""

import json
from typing import Optional
from src.data_models import Incident, RemediationPlan, GovernanceDecision
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from src.agents.tools import TOOLS_SCHEMA, execute_tool


class GovernanceAgent:
    """Meticulous auditor that ensures compliance with safety and policy requirements."""

    def __init__(self, llm_client: Optional[LLMClient] = None, logger: Optional[AgentLogger] = None, max_tokens: int = 250):
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
        system_prompt = """You are a meticulous compliance auditor. Review incidents and remediation plans against company policies.
Check: diagnosis confidence, risk levels, customer impact, remediation risk.
Return JSON with: decision (APPROVE/REJECT_LOW_CONFIDENCE/REJECT_BAD_PLAN/REJECT_POLICY_VIOLATION), reason_code, reason (brief)."""

        # Build user message
        user_message = f"""Review this incident and remediation plan for policy compliance:

Incident:
  Type: {incident.incident_type}
  Root Cause: {incident.root_cause_hypothesis}
  Diagnosis Confidence: {incident.diagnosis_confidence}
  Severity: {incident.severity}

{f"Remediation Plan: {json.dumps(plan.to_dict()[:100])}..." if plan else "No remediation plan provided"}

Call policy tools if needed. Then respond with JSON:
{{"decision": "APPROVE|REJECT_LOW_CONFIDENCE|REJECT_BAD_PLAN|REJECT_POLICY_VIOLATION", "reason_code": "...", "reason": "...", "policies_checked": ["list"]}}"""

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

        # Process tool calls if any
        tool_calls_made = []
        messages = [{"role": "user", "content": user_message}]

        if response.get('tool_calls'):
            tool_calls = response.get('tool_calls', [])
            tool_calls_made = [tc['name'] for tc in tool_calls]

            tool_results = []
            for tool_call in tool_calls:
                tool_result = execute_tool(tool_call['name'], tool_call['input'])
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_call['id'],
                    'content': json.dumps(tool_result)
                })

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