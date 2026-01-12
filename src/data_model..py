"""
Incident management dataclasses for Watchtower MVP.

Defines the agent interface payloads for the incident lifecycle:
- Incident: Detected anomaly with diagnosis (Monitoring & Diagnostic output)
- GovernanceDecision: Policy enforcement checkpoint result
- IncidentReport: Human-readable impact report (Impact & Reporting output)
- ApprovalDecision: Operator approval/rejection (Approval Workflow output)
- RemediationPlan: Proposed fix with execution steps (Remediation Agent output)
- ExecutionResult: Post-execution metrics and impact (Remediation Agent output)
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict


@dataclass
class RecommendedAction:
    """Recommended remediation action for an incident."""

    type: str  # "REROUTE_TRAFFIC", "INHIBIT_ALARMS", etc.
    description: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    estimated_impact: str

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class Incident:
    """Detected network incident with diagnosis and recommendation.

    Produced by Monitoring & Diagnostic Agent; consumed by Governance Checkpoint 1
    and Impact & Reporting Agent.
    """

    incident_id: str
    timestamp: int
    incident_type: str  # "REGIONAL_OUTAGE", "FIBER_CUT", "CORE_CONGESTION", "CELL_FAILURE"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"

    # Scope
    affected_region_ids: List[str]
    affected_cell_ids: List[str]
    affected_services: List[str]  # ["4G_VOICE", "5G_DATA", ...]
    subscribers_impacted: int

    # Diagnosis
    root_cause_hypothesis: str  # Plain-English explanation
    evidence: Dict  # Anomalies and metrics supporting diagnosis

    # Recommendation
    recommended_action: RecommendedAction

    # Follow-up
    follow_up_actions: List[str]

    # Confidence
    diagnosis_confidence: float  # 0–1; root cause confidence

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        result = asdict(self)
        result["recommended_action"] = self.recommended_action.to_dict()
        return result


@dataclass
class GovernanceDecision:
    """Governance checkpoint decision with policy compliance details.

    Produced by Governance Agent at Checkpoints 1, 2, and 3;
    consumed by Supervisor Agent and Audit Logger.
    """

    checkpoint_num: int  # 1, 2, or 3
    decision: str  # "APPROVE", "REJECT", or "NEEDS_MORE_INFO"
    reason: str  # Human-readable explanation
    policy_rules_checked: List[Dict]  # [{"rule_id": "CORE_PROTECTION", "status": "PASS"}, ...]
    confidence_scores: Dict  # {"diagnosis_confidence": 0.85, ...}
    suggested_next_step: str  # What Supervisor should do if rejected or needs info

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class IncidentReport:
    """Human-readable incident report with impact assessment.

    Produced by Impact & Reporting Agent; consumed by Governance Checkpoint 2
    and Approval Workflow.
    """

    incident_id: str
    timestamp: int
    headline: str
    root_cause: str
    affected_subscribers: int
    revenue_at_risk_per_minute: float
    sla_status: str  # "OK", "WARNING", "CRITICAL"
    recommended_action: Dict
    evidence: Dict  # Supporting data for impact assessment
    follow_up_actions: List[str]

    # Confidence
    report_confidence: float  # 0–1; evidence quality and clarity

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class ApprovalDecision:
    """Operator approval or rejection of a remediation action.

    Produced by Approval Workflow; consumed by Remediation Agent.
    """

    incident_id: str
    action_id: str
    timestamp: int

    approver_id: str
    decision: str  # "APPROVED" or "REJECTED"
    rationale: str  # Operator's reasoning

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class RemediationAction:
    """Single remediation action with execution details."""

    action_id: str
    action_type: str
    description: str
    before_state: Dict  # Current metrics
    after_state_expected: Dict  # Predicted metrics post-fix
    execution_steps: List[str]

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class RemediationPlan:
    """Complete remediation plan with multiple actions and rollback.

    Produced by Remediation Agent; consumed by Governance Checkpoint 3.
    """

    incident_id: str
    timestamp: int

    actions: List[RemediationAction]

    rollback_plan: str
    verification_steps: List[str]

    # Confidence
    plan_confidence: float  # 0–1; likelihood of safe successful recovery

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        result = asdict(self)
        result["actions"] = [action.to_dict() for action in self.actions]
        return result


@dataclass
class ImpactSummary:
    """Summary of remediation execution impact."""

    subscribers_recovered: int
    revenue_recovered_per_minute: float
    latency_delta_ms: int
    sla_maintained: bool

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class ExecutionResult:
    """Result of remediation execution with before/after metrics.

    Produced by Remediation Agent (execution phase); consumed by Audit Logger.
    """

    incident_id: str
    action_id: str
    timestamp: int

    status: str  # "SUCCESS", "FAILED"

    before_state: Dict
    after_state: Dict

    impact_summary: Dict  # Computed impact metrics

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


"""
Network entity dataclasses for Watchtower MVP.

Defines the physical/logical network topology components:
- Region: Geographic service areas
- CellSite: Radio access network sites
- BackhaulLink: Transport network connections
- CoreNetwork: Centralized network services
"""

from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Region:
    """Geographic region with multiple cell sites."""

    region_id: str  # "NE", "MW", "SE"
    region_name: str
    subscriber_count: int
    cell_sites: List[str]  # Cell IDs in this region
    sla_target_availability: float  # e.g., 0.999 (99.9%)

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class CellSite:
    """Radio access network cell site."""

    cell_id: str  # "CELL_NE_001"
    region_id: str
    cell_name: str
    subscriber_count: int
    sectors: List[str]  # ["4G", "5G"]
    backhaul_link_ids: List[str]  # Primary and backup links
    admin_status: str  # "UP" or "DOWN"

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class BackhaulLink:
    """Transport network backhaul link."""

    link_id: str  # "BACKHAUL_NE_METRO_PRIMARY"
    source: str  # Starting point
    dest: str  # Destination
    speed_mbps: int  # e.g., 10000
    is_backup: bool
    downstream_cells: List[str]
    admin_status: str  # "UP" or "DOWN"
    base_latency_ms: int = 18  # Baseline latency (default)
    base_utilization_percent: float = 40.0  # Baseline utilization (default)

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class CoreNetwork:
    """Centralized core network services."""

    core_id: str
    aggregation_points: List[str]
    services: List[str]  # ["DNS", "IMS_Voice", "EPC_Gateway"]

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)
