"""Internal task contracts; public investigation DTOs remain unchanged."""

from typing import Any, Literal

from pydantic import Field

from app.hospital.schemas import ClinicalModel
from app.schemas.investigation import AgentResult, SourceRecord

TaskType = Literal["discovery", "timeline", "laboratory", "medication", "referrals", "followup"]
TaskStatus = Literal["planned", "ready", "running", "completed", "failed", "skipped", "cancelled"]


class RetrievalAction(ClinicalModel):
    tool: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class SourceIdentity(ClinicalModel):
    type: str
    id: str
    version: int = Field(ge=1)
    hash: str = Field(min_length=64, max_length=64)

    @classmethod
    def of(cls, record: SourceRecord) -> "SourceIdentity":
        return cls(
            type=record.source.type,
            id=record.source.id,
            version=record.source_version,
            hash=record.source_hash,
        )


class InvestigativeLead(ClinicalModel):
    id: str
    originating_task: str
    source_agent: str
    question: str = Field(min_length=1, max_length=500)
    missing_information: str = Field(min_length=1, max_length=500)
    assigned_agent: str
    task_type: Literal["followup"] = "followup"
    sources: list[SourceIdentity] = Field(min_length=1, max_length=20)
    actions: list[RetrievalAction] = Field(min_length=1, max_length=10)
    priority: int = Field(default=50, ge=0, le=100)
    reason: str = Field(min_length=1, max_length=500)
    status: Literal["proposed", "approved", "rejected", "completed", "unresolved"] = "proposed"
    decision: str | None = None


class InvestigationTask(ClinicalModel):
    id: str
    investigation_id: str
    patient_id: str
    task_type: TaskType
    assigned_agent: str
    objective: str
    reason: str
    dependencies: list[str] = Field(default_factory=list)
    parent_task: str | None = None
    lead_id: str | None = None
    depth: int = Field(default=0, ge=0)
    priority: int = Field(default=50, ge=0, le=100)
    status: TaskStatus = "planned"
    attempts: int = 0
    max_attempts: int = Field(default=1, ge=1, le=3)
    max_tool_calls: int = Field(default=30, ge=1, le=100)
    required_evidence: list[str] = Field(default_factory=list)
    sources: list[SourceIdentity] = Field(default_factory=list)
    actions: list[RetrievalAction] = Field(default_factory=list)
    result_refs: list[SourceIdentity] = Field(default_factory=list)
    error: str | None = None


class TaskResult(ClinicalModel):
    task_id: str
    agent: str
    execution_id: str | None = None
    analysis: AgentResult = Field(default_factory=AgentResult)
    records: list[SourceRecord] = Field(default_factory=list)
    leads: list[InvestigativeLead] = Field(default_factory=list)


class InvestigationContext(ClinicalModel):
    investigation_id: str
    patient_id: str
    objective: str
    manifest: list[SourceIdentity] = Field(default_factory=list)
    missing_modalities: list[str] = Field(default_factory=list)
    tasks: list[InvestigationTask] = Field(default_factory=list)
    leads: list[InvestigativeLead] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    stop_reason: str = "evidence_exhaustion"
    duplicates_suppressed: int = 0
    candidate_origins: dict[str, dict[str, str]] = Field(default_factory=dict)
