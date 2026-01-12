import yaml
import random
from typing import Optional
from src.data_models import Incident, RemediationPlan, RemediationAction

class RemediationAgent:
    def __init__(self, runbook_path='config/runbooks.yaml'):
        try:
            with open(runbook_path, 'r') as f:
                self.runbooks = yaml.safe_load(f)
        except FileNotFoundError:
            self.runbooks = {}

    def create_plan(self, incident: Incident) -> Optional[RemediationPlan]:
        runbook = self.runbooks.get(incident.incident_type)
        if not runbook:
            return None

        # Fill in action template
        action_description = runbook['action_template']
        
        # Populate template fields for the action
        truck_id = f"TRK-{random.randint(100, 999)}"
        target_site = "Unknown"
        if incident.affected_cell_ids:
            target_site = incident.affected_cell_ids[0] # Use the first affected cell as target

        action_description = action_description.format(truck_id=truck_id, target_site=target_site)

        # Create a single RemediationAction
        remediation_action = RemediationAction(
            action_type=incident.incident_type, # Using incident type as action type for simplicity
            description=action_description,
            before_state={'incident_details': incident.to_dict()}, # Store incident details as before state
            after_state_expected={}, # Placeholder
            execution_steps=[action_description] # Simple execution step
        )

        # Create the RemediationPlan
        plan = RemediationPlan(
            incident_id=incident.incident_id,
            actions=[remediation_action],
            rollback_plan=f"Manual rollback for {incident.incident_type}",
            verification_steps=[f"Verify service restored at {target_site}"],
            plan_confidence=incident.diagnosis_confidence # Use diagnosis confidence as plan confidence
        )
        
        return plan