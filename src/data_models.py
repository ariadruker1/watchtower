"""
Incident management dataclasses for Watchtower MVP.

Defines the agent interface payloads for the incident lifecycle,
and network entity dataclasses for the physical/logical network topology components.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import time
import uuid


@dataclass
class Alert:
    tower_id: str
    metric: str
    value: float
    timestamp: float = field(default_factory=time.time)
    message: str = ""

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

    incident_type: str  # "REGIONAL_OUTAGE", "FIBER_CUT", "CORE_CONGESTION", "CELL_FAILURE"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    incident_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: int = field(default_factory=lambda: int(time.time()))

    # Scope
    affected_region_ids: List[str] = field(default_factory=list)
    affected_cell_ids: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)  # ["4G_VOICE", "5G_DATA", ...]
    subscribers_impacted: int = 0

    # Diagnosis
    root_cause_hypothesis: str = ""  # Plain-English explanation
    evidence: Dict = field(default_factory=dict)  # Anomalies and metrics supporting diagnosis

    # Recommendation
    recommended_action: Optional[RecommendedAction] = None

    # Follow-up
    follow_up_actions: List[str] = field(default_factory=list)

    # Confidence
    diagnosis_confidence: float = 0.0  # 0–1; root cause confidence

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        result = asdict(self)
        if self.recommended_action:
            result["recommended_action"] = self.recommended_action.to_dict()
        return result


@dataclass
class GovernanceDecision:
    """Governance checkpoint decision with policy compliance details.

    Produced by Governance Agent; consumed by Supervisor Agent.
    """

    decision: str  # "APPROVE", "REJECT_LOW_CONFIDENCE", "REJECT_BAD_PLAN", "REJECT_POLICY_VIOLATION"
    reason_code: str  # Machine-readable reason code
    reason: str  # Human-readable explanation
    policies_checked: List[str] = field(default_factory=list)  # List of policies evaluated

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
    recommended_action: Dict = field(default_factory=dict)
    evidence: Dict = field(default_factory=dict)  # Supporting data for impact assessment
    follow_up_actions: List[str] = field(default_factory=list)

    # Confidence
    report_confidence: float = 0.0  # 0–1; evidence quality and clarity

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

    action_type: str
    description: str
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    before_state: Dict = field(default_factory=dict)  # Current metrics
    after_state_expected: Dict = field(default_factory=dict)  # Predicted metrics post-fix
    execution_steps: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class RemediationPlan:
    """Complete remediation plan with multiple actions and rollback.

    Produced by Remediation Agent; consumed by Governance Checkpoint 3.
    """

    incident_id: str
    timestamp: int = field(default_factory=lambda: int(time.time()))

    actions: List[RemediationAction] = field(default_factory=list)

    rollback_plan: str = ""
    verification_steps: List[str] = field(default_factory=list)

    # Confidence
    plan_confidence: float = 0.0  # 0–1; likelihood of safe successful recovery

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        result = asdict(self)
        result["actions"] = [action.to_dict() for action in self.actions]
        return result


@dataclass
class ImpactSummary:
    """Summary of remediation execution impact."""

    subscribers_recovered: int = 0
    revenue_recovered_per_minute: float = 0.0
    latency_delta_ms: int = 0
    sla_maintained: bool = False

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
    timestamp: int = field(default_factory=lambda: int(time.time()))

    status: str = ""  # "SUCCESS", "FAILED"

    before_state: Dict = field(default_factory=dict)
    after_state: Dict = field(default_factory=dict)

    impact_summary: Dict = field(default_factory=dict)  # Computed impact metrics

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class Region:
    """Geographic region with multiple cell sites."""

    region_id: str  # "NE", "MW", "SE"
    region_name: str
    subscriber_count: int
    cell_sites: List[str] = field(default_factory=list)  # Cell IDs in this region
    sla_target_availability: float = 0.0  # e.g., 0.999 (99.9%)

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
    sectors: List[str] = field(default_factory=list)  # ["4G", "5G"]
    backhaul_link_ids: List[str] = field(default_factory=list)  # Primary and backup links
    admin_status: str = "UP"  # "UP" or "DOWN"
    power_status: str = "ONLINE" # New field for power outage scenario

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class BackhaulLink:
    """Transport network backhaul link."""

    link_id: str  # "BACKHAUL_NE_METRO_PRIMARY"
    source: str  # Starting point
    dest: str  # Destination
    speed_mbps: int = 0
    is_backup: bool = False
    downstream_cells: List[str] = field(default_factory=list)
    admin_status: str = "UP"  # "UP" or "DOWN"
    base_latency_ms: int = 18  # Baseline latency (default)
    base_utilization_percent: float = 40.0  # Baseline utilization (default)
    fiber_status: str = "OPERATIONAL" # New field for fiber cut scenario

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)


@dataclass
class CoreNetwork:
    """Centralized core network services."""

    core_id: str
    aggregation_points: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)  # ["DNS", "IMS_Voice", "EPC_Gateway"]

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)
