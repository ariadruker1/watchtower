from typing import Optional
from src.data_models import Alert, Incident
import time # Needed for timestamp if not default factory

class DiagnosticAgent:
    def diagnose_alerts(self, alerts: list[Alert]) -> Optional[Incident]:
        if not alerts:
            return None

        # Helper to extract affected tower IDs
        def get_affected_cell_ids(alerts_list):
            return list(set([a.tower_id for a in alerts_list]))

        # --- Rule for FIBER_CUT ---
        # High confidence if multiple towers go down simultaneously.
        down_towers = {a.tower_id for a in alerts if a.metric == 'status' and a.value == -1}
        if len(down_towers) > 1:
            affected_cell_ids = list(down_towers)
            return Incident(
                incident_type='FIBER_CUT',
                severity='CRITICAL',
                affected_cell_ids=affected_cell_ids,
                root_cause_hypothesis=f"Multiple cell sites ({', '.join(affected_cell_ids)}) have lost connectivity, indicating a potential fiber cut.",
                evidence={'alerts': [a.message for a in alerts]},
                diagnosis_confidence=0.9
            )

        # --- Rule for POWER_OUTAGE ---
        # High confidence if a single tower is DOWN and reports a power level of 0.
        power_alerts = {a.tower_id: a.value for a in alerts if a.metric == 'power_level'}
        for tower_id in down_towers:
            if power_alerts.get(tower_id) == 0.0:
                return Incident(
                    incident_type='POWER_OUTAGE',
                    severity='CRITICAL',
                    affected_cell_ids=[tower_id],
                    root_cause_hypothesis=f"Cell site {tower_id} has experienced a complete power failure.",
                    evidence={'alerts': [a.message for a in alerts]},
                    diagnosis_confidence=0.95
                )

        # --- Rule for SIGNAL_INTERFERENCE ---
        # Medium confidence if a tower is in ALARM and has fluctuating signal strength.
        alarm_towers = {a.tower_id for a in alerts if a.metric == 'status' and a.value == 0}
        if alarm_towers:
            affected_cell_ids = list(alarm_towers)
            return Incident(
                incident_type='SIGNAL_INTERFERENCE',
                severity='HIGH',
                affected_cell_ids=affected_cell_ids,
                root_cause_hypothesis=f"Cell site {affected_cell_ids[0]} is experiencing significant signal degradation likely due to RF interference.",
                evidence={'alerts': [a.message for a in alerts]},
                diagnosis_confidence=0.85
            )

        # Default for any other single-tower outage
        if len(down_towers) == 1:
             tower_id = list(down_towers)[0]
             return Incident(
                incident_type='POWER_OUTAGE', # Assume power outage as a default for single tower failure
                severity='CRITICAL',
                affected_cell_ids=[tower_id],
                root_cause_hypothesis=f"Single cell site {tower_id} is down, defaulting to power outage as primary suspect.",
                evidence={'alerts': [a.message for a in alerts]},
                diagnosis_confidence=0.8
            )

        return None