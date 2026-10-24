"""Investigation domain; source records remain immutable."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import UTCDateTime


class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed',"
            "'completed_with_limitations','failed','cancelled')",
            name="status",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("case_datasets.id"))
    question: Mapped[str] = mapped_column(String)
    requested_by: Mapped[str] = mapped_column(String, default="local")
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class RunRow:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    investigation_id: Mapped[UUID] = mapped_column(ForeignKey("investigations.id"), index=True)


class InvestigationEvent(RunRow, Base):
    __tablename__ = "investigation_events"
    __table_args__ = (UniqueConstraint("investigation_id", "sequence"),)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime)


class InvestigationStage(RunRow, Base):
    __tablename__ = "investigation_stages"
    __table_args__ = (UniqueConstraint("investigation_id", "stage_key", "attempt"),)
    stage_key: Mapped[str] = mapped_column(String)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class AgentExecution(RunRow, Base):
    __tablename__ = "agent_executions"
    __table_args__ = (UniqueConstraint("investigation_id", "agent_key", "attempt"),)
    agent_key: Mapped[str] = mapped_column(String)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    task_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ToolCall(RunRow, Base):
    __tablename__ = "tool_calls"
    agent_execution_id: Mapped[UUID] = mapped_column(ForeignKey("agent_executions.id"))
    tool_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    sanitized_args: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    error_code: Mapped[str | None] = mapped_column(String)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class EvidenceRef(RunRow, Base):
    __tablename__ = "evidence_refs"
    anchor: Mapped[dict[str, Any]] = mapped_column(JSON)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Finding(RunRow, Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("investigation_id", "logical_key"),)
    logical_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_links"
    finding_id: Mapped[UUID] = mapped_column(ForeignKey("findings.id"), primary_key=True)
    evidence_ref_id: Mapped[UUID] = mapped_column(ForeignKey("evidence_refs.id"), primary_key=True)
    relationship: Mapped[str] = mapped_column(String, primary_key=True)
    validation_status: Mapped[str] = mapped_column(String)


class Report(RunRow, Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("investigation_id", "version"),)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ChatMessage(RunRow, Base):
    __tablename__ = "investigation_chat_messages"
    __table_args__ = (UniqueConstraint("investigation_id", "sequence"),)
    sequence: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict[str, Any]] = mapped_column(JSON)
