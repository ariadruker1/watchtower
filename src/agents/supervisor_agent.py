from .monitoring_agent import MonitoringAgent
from .diagnostic_agent import DiagnosticAgent
from .remediation_agent import RemediationAgent
from .governance_agent import GovernanceAgent
from src.data_models import RemediationPlan, Incident
from collections import defaultdict
import time
from typing import Optional

class SupervisorAgent:
    def __init__(self):
        # Initialize all subordinate agents
        self.monitoring_agent = MonitoringAgent()
        self.diagnostic_agent = DiagnosticAgent()
        self.remediation_agent = RemediationAgent()
        self.governance_agent = GovernanceAgent()
        
        # State attributes
        self.remediation_plan: Optional[RemediationPlan] = None
        self.human_approval_required = False
        self.current_incident: Optional[Incident] = None

        # For confidence boosting
        self.incident_counts = defaultdict(int)
        self.incident_timestamps = defaultdict(float)
        self.confidence_boost_threshold = 2  # Boost after seeing the same incident twice
        self.persistence_window = 10  # seconds

    def _get_incident_key(self, incident: Incident):
        """Creates a unique key for an incident based on its type and affected cells."""
        if not incident:
            return None
        return (incident.incident_type, tuple(sorted(incident.affected_cell_ids)))

    def process_telemetry(self, telemetry_data: dict):
        """The main entry point for the supervisor's workflow."""
        # Reset state for the current tick
        self.human_approval_required = False
        
        alerts = self.monitoring_agent.analyze_telemetry(telemetry_data)
        
        if not alerts:
            self.current_incident = None
            return "No alerts. System nominal."

        incident = self.diagnostic_agent.diagnose_alerts(alerts)
        if not incident:
            self.current_incident = None
            return "Alerts detected, but no clear incident diagnosed."

        # --- Confidence Boosting Logic ---
        incident_key = self._get_incident_key(incident)
        current_time = time.time()
        
        # Check if the same incident has been seen recently
        if (current_time - self.incident_timestamps.get(incident_key, 0)) < self.persistence_window:
            self.incident_counts[incident_key] += 1
        else:
            self.incident_counts[incident_key] = 1 # Reset count if it's been a while
        
        self.incident_timestamps[incident_key] = current_time

        boost_message = ""
        if self.incident_counts[incident_key] >= self.confidence_boost_threshold:
            original_confidence = incident.diagnosis_confidence # Use diagnosis_confidence
            incident.diagnosis_confidence = min(original_confidence * 1.2, 1.0) # Boost confidence by 20%
            boost_message = f"Confidence boosted to {incident.diagnosis_confidence:.2f} due to persistence."

        self.current_incident = incident
        log_message = f"Incident Diagnosed: {incident.incident_type} (Confidence: {incident.diagnosis_confidence:.2f}). {boost_message}"

        # --- Governance Check ---
        is_approved_by_governance = self.governance_agent.evaluate(incident)
        if not is_approved_by_governance:
            return f"{log_message} | Plan halted: Confidence below policy threshold of {self.governance_agent.min_confidence}."
        
        log_message += " | Passed Governance."

        # --- Remediation Planning ---
        plan = self.remediation_agent.create_plan(incident)
        if not plan:
            return f"{log_message} | No remediation plan found."

        self.remediation_plan = plan
        self.human_approval_required = True # Flag for the UI
        
        # Get action from the first action in the plan
        action_summary = "No action proposed."
        if plan.actions:
            action_summary = plan.actions[0].description
            
        return f"{log_message} | Remediation plan created: '{action_summary}'. Awaiting human approval."