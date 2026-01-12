import yaml
from src.data_models import Incident

class GovernanceAgent:
    def __init__(self, policy_path='watchtower_mvp/config/policy.yaml'):
        try:
            with open(policy_path, 'r') as f:
                self.policy = yaml.safe_load(f)
        except FileNotFoundError:
            self.policy = {}
        self.min_confidence = self.policy.get('min_confidence_threshold', 0.9)

    def evaluate(self, incident: Incident) -> bool:
        """
        Evaluates if the incident meets the minimum confidence threshold defined in the policy.
        """
        if not incident:
            return False
        return incident.diagnosis_confidence >= self.min_confidence