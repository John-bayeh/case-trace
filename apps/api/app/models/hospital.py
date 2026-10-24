"""Immutable hospital source models; no evaluator or investigation tables."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.models.base import Base
from app.models.types import UTCDateTime


class CaseDataset(Base):
    __tablename__ = "case_datasets"
    __table_args__ = (UniqueConstraint("case_id", "dataset_version"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    case_id: Mapped[str] = mapped_column(String)
    dataset_version: Mapped[str] = mapped_column(String)
    seed_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String)
    seeded_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Source:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    source_system: Mapped[str] = mapped_column(String, default="synthetic_his")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    # Validated clinical allowlist only; original offsets and date precision survive.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Patient(Source, Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("dataset_id", "synthetic_mrn"),
        CheckConstraint("is_synthetic = 1", name="synthetic_only"),
    )
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("case_datasets.id"))
    synthetic_mrn: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Encounter(Source, Base):
    __tablename__ = "encounters"
    __table_args__ = (
        UniqueConstraint("id", "patient_id"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="chronology"),
        Index("ix_encounters_patient_time", "patient_id", "started_at", "external_id"),
    )
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"))
    type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String)
    provider_name: Mapped[str] = mapped_column(String)
    facility_label: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class ScopedSource(Source):
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Any, ...]:
        return (
            ForeignKeyConstraint(
                ["encounter_id", "patient_id"], ["encounters.id", "encounters.patient_id"]
            ),
        )


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    storage_key: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    synthetic_label: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ClinicalDocument(ScopedSource, Base):
    __tablename__ = "clinical_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["encounter_id", "patient_id"], ["encounters.id", "encounters.patient_id"]
        ),
        UniqueConstraint("id", "patient_id"),
    )
    document_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    author_label: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="original")
    event_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    authored_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    signed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    current_version_id: Mapped[UUID | None] = mapped_column(Uuid)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("clinical_documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"))
    text_content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    amended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("document_versions.id"))


class DocumentLinked(ScopedSource):
    source_document_id: Mapped[UUID | None] = mapped_column(Uuid)

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Any, ...]:
        return (
            ForeignKeyConstraint(
                ["encounter_id", "patient_id"], ["encounters.id", "encounters.patient_id"]
            ),
            ForeignKeyConstraint(
                ["source_document_id", "patient_id"],
                ["clinical_documents.id", "clinical_documents.patient_id"],
            ),
        )


class ClinicalEvent(DocumentLinked, Base):
    __tablename__ = "clinical_events"
    event_type: Mapped[str] = mapped_column(String)
    event_time: Mapped[datetime | None] = mapped_column(UTCDateTime)
    time_precision: Mapped[str] = mapped_column(String)
    time_raw: Mapped[str | None] = mapped_column(String)
    documented_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    description: Mapped[str] = mapped_column(Text)


class LabOrder(ScopedSource, Base):
    __tablename__ = "lab_orders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["encounter_id", "patient_id"], ["encounters.id", "encounters.patient_id"]
        ),
        UniqueConstraint("id", "patient_id"),
    )
    ordered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String)
    panel_code: Mapped[str | None] = mapped_column(String)


class LabResult(DocumentLinked, Base):
    __tablename__ = "lab_results"
    lab_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("lab_orders.id"))
    analyte_code: Mapped[str | None] = mapped_column(String)
    test_name: Mapped[str] = mapped_column(String)
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String)
    reference_low: Mapped[float | None] = mapped_column(Float)
    reference_high: Mapped[float | None] = mapped_column(Float)
    collected_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reported_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String)
    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("lab_results.id"))


class MedicationEvent(DocumentLinked, Base):
    __tablename__ = "medication_events"
    record_type: Mapped[str] = mapped_column(String, default="documented_history")
    drug_name: Mapped[str] = mapped_column(String)
    generic_name: Mapped[str | None] = mapped_column(String)
    dose: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String)
    route: Mapped[str | None] = mapped_column(String)
    frequency: Mapped[str | None] = mapped_column(String)
    ordered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    effective_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    administered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    discontinued_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    prescriber: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    parent_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("medication_events.id"))


class ImagingStudy(ScopedSource, Base):
    __tablename__ = "imaging_studies"
    modality: Mapped[str] = mapped_column(String)
    body_region: Mapped[str] = mapped_column(String)
    ordered_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    performed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reported_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    report_document_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinical_documents.id"))
    status: Mapped[str] = mapped_column(String)


class ImagingAsset(Base):
    __tablename__ = "imaging_assets"
    __table_args__ = (UniqueConstraint("study_id", "asset_id"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    study_id: Mapped[UUID] = mapped_column(ForeignKey("imaging_studies.id"))
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"))
    series_label: Mapped[str | None] = mapped_column(String)
    asset_kind: Mapped[str] = mapped_column(String)
    ordinal: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class Referral(ScopedSource, Base):
    __tablename__ = "referrals"
    origin_service: Mapped[str] = mapped_column(String)
    destination_service: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    requested_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    scheduled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinical_documents.id"))


class Diagnosis(ScopedSource, Base):
    __tablename__ = "diagnoses"
    name: Mapped[str] = mapped_column(String)
    code_system: Mapped[str | None] = mapped_column(String)
    code: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    diagnosed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Symptom(ScopedSource, Base):
    __tablename__ = "symptoms"
    name: Mapped[str] = mapped_column(String)
    onset_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    severity: Mapped[str | None] = mapped_column(String)
    frequency: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)


class DiagnosticReport(ScopedSource, Base):
    __tablename__ = "diagnostic_reports"
    report_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    issued_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    conclusion: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("clinical_documents.id"))
    imaging_study_id: Mapped[UUID | None] = mapped_column(ForeignKey("imaging_studies.id"))


class ReportObservation(Base):
    __tablename__ = "report_observations"
    report_id: Mapped[UUID] = mapped_column(ForeignKey("diagnostic_reports.id"), primary_key=True)
    observation_id: Mapped[UUID] = mapped_column(ForeignKey("lab_results.id"), primary_key=True)
