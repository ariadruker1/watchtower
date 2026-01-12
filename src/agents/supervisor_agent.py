"""Supervisor Agent: Orchestrator of incident response workflow with token budgeting."""

from .monitoring_agent import MonitoringAgent
from .diagnostic_agent import DiagnosticAgent
from .remediation_agent import RemediationAgent
from .governance_agent import GovernanceAgent
from src.data_models import RemediationPlan, Incident
from src.llm_client import LLMClient
from src.agent_logger import AgentLogger
from collections import defaultdict
import time
from typing import Optional


class SupervisorAgent:
    """Operations chief orchestrating multi-agent incident response with token budgeting."""

    def __init__(self, logger: Optional[AgentLogger] = None, max_budget: int = 5000):
        self.logger = logger or AgentLogger()

        # Token budget - redistributed for better reasoning
        self.max_budget = max_budget
        self.current_budget = max_budget

        # Shared LLM client for all agents (set high to allow agents to make full requests)
        self.llm_client = LLMClient(max_tokens_per_call=2000)

        # Initialize all subordinate agents with shared LLM client and logger
        # Token distribution: Diagnostic=2000 (multi-round tool calling) + Remediation=1500 (planning) + Governance=1000 (validation) + buffer=500
        self.monitoring_agent = MonitoringAgent()
        self.diagnostic_agent = DiagnosticAgent(self.llm_client, self.logger, max_tokens=2000)
        self.remediation_agent = RemediationAgent(self.llm_client, self.logger, max_tokens=1500)
        self.governance_agent = GovernanceAgent(self.llm_client, self.logger, max_tokens=1000)

        # State attributes
        self.remediation_plan: Optional[RemediationPlan] = None
        self.human_approval_required = False
        self.current_incident: Optional[Incident] = None

        # For confidence boosting
        self.incident_counts = defaultdict(int)
        self.incident_timestamps = defaultdict(float)
        self.confidence_boost_threshold = 2
        self.persistence_window = 10

    def _get_incident_key(self, incident: Incident):
        """Creates a unique key for an incident."""
        if not incident:
            return None
        return (incident.incident_type, tuple(sorted(incident.affected_cell_ids)))

    def _check_token_budget(self) -> bool:
        """Check if we have tokens remaining."""
        used = self.llm_client.total_tokens_used
        return used < self.max_budget

    def _log_message(self, msg: str):
        """Log a message for UI display."""
        if self.logger:
            self.logger.log_interaction('SupervisorAgent', msg, '', [], 0, True)

    def process_telemetry(self, telemetry_data: dict) -> str:
        """Main workflow orchestration with token budget enforcement."""
        # Reset state
        self.human_approval_required = False
        self.remediation_plan = None
        self.llm_client.reset_token_count()
        self.logger.clear_incident_logs()

        # --- Monitoring ---
        alerts = self.monitoring_agent.analyze_telemetry(telemetry_data)

        if not alerts:
            self.current_incident = None
            return "No alerts. System nominal."

        # --- Diagnostics with retries ---
        incident = self.diagnostic_agent.diagnose_alerts(alerts)
        if not incident:
            self.current_incident = None
            return "Alerts detected, but no clear diagnosis."

        # --- Confidence Boosting ---
        incident_key = self._get_incident_key(incident)
        current_time = time.time()

        if (current_time - self.incident_timestamps.get(incident_key, 0)) < self.persistence_window:
            self.incident_counts[incident_key] += 1
        else:
            self.incident_counts[incident_key] = 1

        self.incident_timestamps[incident_key] = current_time

        boost_message = ""
        if self.incident_counts[incident_key] >= self.confidence_boost_threshold:
            original_confidence = incident.diagnosis_confidence
            incident.diagnosis_confidence = min(original_confidence * 1.2, 1.0)
            boost_message = f"Confidence boosted to {incident.diagnosis_confidence:.2f} due to persistence."

        self.current_incident = incident
        log_message = f"Incident Diagnosed: {incident.incident_type} (Confidence: {incident.diagnosis_confidence:.2f}). {boost_message}"

        # Check token budget
        if not self._check_token_budget():
            return f"{log_message} | Token budget exceeded. Halting further processing."

        # --- Remediation Planning ---
        plan = self.remediation_agent.create_plan(incident)
        if not plan:
            return f"{log_message} | No remediation plan created."

        log_message += " | Remediation plan created."

        if not self._check_token_budget():
            return f"{log_message} | Token budget approaching limit. Escalating to human review."

        # --- Governance Evaluation ---
        governance_decision = self.governance_agent.evaluate(incident, plan)

        # Handle governance rejection with feedback loop (max 1 retry)
        if governance_decision.decision != 'APPROVE':
            if governance_decision.decision == 'REJECT_LOW_CONFIDENCE' and self._check_token_budget():
                # Try diagnostic again with feedback
                feedback = f"Initial confidence {incident.diagnosis_confidence} was rejected. Need stronger evidence."
                incident2 = self.diagnostic_agent.diagnose_alerts(alerts, feedback)
                if incident2 and incident2.diagnosis_confidence > incident.diagnosis_confidence:
                    incident = incident2
                    log_message += " | Re-diagnosed with higher confidence."

                    # Re-evaluate governance
                    if not self._check_token_budget():
                        log_message += " | Token budget limit reached after diagnostic retry."
                    else:
                        governance_decision = self.governance_agent.evaluate(incident, plan)

            if governance_decision.decision != 'APPROVE':
                log_message += f" | Governance: {governance_decision.reason_code} - {governance_decision.reason}"
                return log_message

        log_message += " | Passed Governance Review."

        # --- Human Approval ---
        self.remediation_plan = plan
        self.human_approval_required = True

        action_summary = "No actions"
        if plan.actions:
            action_summary = " | ".join([a.description for a in plan.actions[:2]])

        token_usage = self.llm_client.get_token_usage_summary()
        log_message += f" | Plan ready. [Tokens: {token_usage['total_tokens']}/{self.max_budget}] Awaiting human approval."

        return log_message