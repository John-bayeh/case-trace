"""Typed runtime contracts. Clinical assertions require independently resolved anchors."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.clinical.diagnostic_models import DiagnosticComparison
from app.clinical.longitudinal_models import LongitudinalEvidence
from app.clinical.relationship_models import RelationshipEvidence
from app.hospital.schemas import ClinicalModel, Identifier
from app.schemas.provenance import (
    Anchor as Anchor,
)
from app.schemas.provenance import (
    SourceRef as SourceRef,
)
from app.schemas.provenance import (
    SourceType as SourceType,
)

RunStatus = Literal[
    "queued", "running", "completed", "completed_with_limitations", "failed", "cancelled"
]


class CreateInvestigation(ClinicalModel):
    patient_id: Identifier
    objective: Literal[
        "full_record_investigation",
        "timeline_investigation",
        "contradiction_investigation",
        "medication_investigation",
        "laboratory_investigation",
        "followup_investigation",
        "hypothesis_investigation",
    ] = "full_record_investigation"


class InvestigationHistoryItem(ClinicalModel):
    id: str
    patient_id: str
    case_id: str
    objective: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    current_stage: str | None = None


class InvestigationHistory(ClinicalModel):
    items: list[InvestigationHistoryItem]
    total: int
    limit: int
    offset: int


class SourceRecord(ClinicalModel):
    source: SourceRef
    source_version: int
    source_hash: str
    data: dict[str, Any]
    representation: Literal["source", "search_hit"] = "source"
    representation_hash: str | None = None


class ToolInput(ClinicalModel):
    patient_id: Identifier
    record_id: Identifier | None = None
    other_id: Identifier | None = None
    query: str = Field(default="", max_length=200)
    test_name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class LabComparison(ClinicalModel):
    direction: Literal["increasing", "decreasing", "unchanged"]
    change_absolute: float
    change_percent: float | None


class ToolResult(ClinicalModel):
    status: Literal["success", "empty", "partial"]
    records: list[SourceRecord]
    source_refs: list[SourceRef]
    total: int
    has_more: bool
    retrieved_at: datetime
    analysis: LabComparison | None = None
    timeline: list["TimelineEvent"] = Field(default_factory=list)


class Candidate(ClinicalModel):
    type: Literal[
        "timeline_contradiction",
        "laboratory_change",
        "medication_change",
        "documentation_delay",
        "missing_evidence",
        "clinical_relationship",
    ]
    title: str = Field(min_length=1, max_length=200)
    claim: str = Field(min_length=1, max_length=2000)
    claim_kind: Literal["observation", "chronology", "interpretation", "hypothesis"]
    rule: Literal[
        "field_observation",
        "lab_change",
        "record_series",
        "longitudinal_followup",
        "clinical_relationship",
        "review_before_result",
        "onset_conflict",
        "interpretation",
    ]
    anchors: list[Anchor] = Field(min_length=1, max_length=20)
    alternatives: list[str] = Field(default_factory=list, max_length=10)
    limitations: list[str] = Field(default_factory=list, max_length=10)
    relationship: RelationshipEvidence | None = None
    longitudinal: LongitudinalEvidence | None = None


class Hypothesis(ClinicalModel):
    comparison: DiagnosticComparison | None = None
    explanation: str = Field(max_length=1500)
    supports: list[Anchor] = Field(default_factory=list, max_length=20)
    weakens: list[Anchor] = Field(default_factory=list, max_length=20)
    missing_evidence: list[str] = Field(min_length=1, max_length=10)
    verdict: Literal["supported", "weakened", "inconclusive"] = "inconclusive"
    alternatives: list[str] = Field(default_factory=list, max_length=10)
    limitations: list[str] = Field(default_factory=list, max_length=10)


class AgentResult(ClinicalModel):
    candidates: list[Candidate] = Field(default_factory=list, max_length=20)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=10)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class Check(ClinicalModel):
    type: str
    status: Literal["passed", "failed", "inconclusive"]
    message: str


class Verification(ClinicalModel):
    status: Literal["verified", "rejected", "inconclusive"]
    checks: list[Check]
    classification: str


class Finding(Candidate):
    id: str
    investigation_id: str
    status: Literal["proposed", "verified", "rejected", "unresolved"]
    support_level: Literal["strong", "limited", "insufficient"]
    verification: Verification
    created_at: datetime
    verified_at: datetime | None = None


class TimelineEvent(ClinicalModel):
    id: str
    source: SourceRef
    timestamp: str | None
    timestamp_type: str
    precision: Literal["instant", "day", "unknown"]
    timestamps: dict[str, str | None]
    title: str


class ActivityEvent(ClinicalModel):
    id: str
    investigation_id: str
    sequence: int
    type: str
    timestamp: datetime
    payload: dict[str, Any]
    message: str = ""
    execution_status: str = ""


class Report(ClinicalModel):
    investigation_id: str
    status: RunStatus
    summary: dict[str, str]
    timeline: list[TimelineEvent]
    verified_findings: list[Finding]
    rejected_findings: list[Finding]
    unresolved_findings: list[Finding]
    hypotheses: list[Hypothesis]
    limitations: list[str]
    generated_at: datetime
    execution_mode: str
    execution_config: dict[str, str | int] = Field(default_factory=dict)


class CreationResponse(ClinicalModel):
    investigation_id: str
    status: RunStatus
    patient_id: str
    created_at: datetime


class Progress(ClinicalModel):
    current_stage: str
    completed_stages: int
    total_stages: int
    percent: int


class AgentStatusInfo(ClinicalModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime | None
    completed_at: datetime | None


class InvestigationState(ClinicalModel):
    id: str
    patient_id: str
    case_id: str
    objective: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    version: int
    progress: Progress
    agents: list[AgentStatusInfo]
    finding_summary: dict[str, int]
    timeline: list[TimelineEvent]
    hypotheses: list[Hypothesis]
    limitations: list[str]


class EventPage(ClinicalModel):
    items: list[ActivityEvent]
    total: int


class FindingPage(ClinicalModel):
    items: list[Finding]
    total: int
