"""Documented diagnostic workflow; absence of documentation is never absent care."""

from typing import Literal

from pydantic import Field

from app.hospital.schemas import ClinicalModel
from app.schemas.provenance import Anchor, SourceRef

StageName = Literal[
    "ordered",
    "performed",
    "specimen_collected",
    "finalized",
    "routed",
    "acknowledged",
    "patient_notification",
    "recommended",
    "scheduled",
    "completed",
    "administrative_closure",
]
WorkflowState = Literal["documented", "partial", "unknown", "conflicting"]
STAGES: tuple[StageName, ...] = (
    "ordered",
    "performed",
    "specimen_collected",
    "finalized",
    "routed",
    "acknowledged",
    "patient_notification",
    "recommended",
    "scheduled",
    "completed",
    "administrative_closure",
)


class WorkflowSource(ClinicalModel):
    source: SourceRef
    version: int
    hash: str


class ResultSearchScope(ClinicalModel):
    # Unfiltered selected-patient snapshots, not a claim of access to external care.
    sources: list[WorkflowSource] = Field(default_factory=list, max_length=120)
    complete: bool = False
    document_limit: int = Field(default=20, ge=1, le=20)
    appointment_coverage: Literal["referral_fields_only"] = "referral_fields_only"
    categories: list[str] = Field(
        default_factory=lambda: ["diagnostic_report", "document", "encounter", "referral"]
    )


class WorkflowObservation(ClinicalModel):
    stage: StageName
    state: WorkflowState
    anchor: Anchor
    event_time_field: str | None = None
    timestamps: dict[str, str | None] = Field(default_factory=dict)
    # Preserve narrative dates literally; do not turn a date into an aware instant.
    literal_dates: list[str] = Field(default_factory=list, max_length=10)


class WorkflowStage(ClinicalModel):
    stage: StageName
    state: WorkflowState
    observations: list[WorkflowObservation] = Field(default_factory=list, max_length=40)


class ResultWorkflow(ClinicalModel):
    result_id: str
    search: ResultSearchScope
    lifecycle: list[WorkflowStage] = Field(min_length=11, max_length=11)
    attribution: Literal["explicit_link", "unique_result_context"]
