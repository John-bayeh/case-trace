"""Maintenance-only source validation. Never imported by agent code."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from app.hospital.assets import AssetInfo, LocalAssetStorage
from app.hospital.diagnostics import Diagnostic, ValidationReport
from app.hospital.manifest import validate_manifest
from app.hospital.schemas import ClinicalCase, Document, ImagingAsset

# Editor/evaluator sections are discarded before any clinical diagnostics.
EDITOR_FIELDS = {
    "title",
    "description",
    "metadata",
    "ground_truth",
    "investigation_target",
    "timeline_relationships",
    "evidence_relationships",
    "red_herrings",
    "noise",
}


class CaseValidationError(ValueError):
    def __init__(self, message: str, report: ValidationReport | None = None):
        super().__init__(message)
        self.report = report


@dataclass(frozen=True)
class ValidatedCase:
    clinical: ClinicalCase
    assets: dict[str, AssetInfo]
    report: ValidationReport | None = None


def validate_case(path: Path, storage: LocalAssetStorage) -> ValidatedCase:
    report = ValidationReport()

    def add(
        code: str,
        description: str,
        kind: str | None = None,
        record_id: str | None = None,
        field: str | None = None,
        severity: Literal["error", "warning", "info"] = "error",
        file: Path = path,
    ) -> None:
        report.diagnostics.append(
            Diagnostic(
                report.case_id,
                str(file),
                kind,
                record_id,
                field,
                code,
                description,
                severity,
            )
        )

    def finish() -> None:
        if not report.valid:
            raise CaseValidationError(
                "; ".join(
                    f"{d.file}: {d.record_id or ''} {d.description}"
                    for d in report.diagnostics
                    if d.severity == "error"
                ),
                report,
            )

    try:
        source_bytes = path.read_bytes()
        raw: Any = json.loads(source_bytes.decode("utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("case root must be an object")
    except (OSError, ValueError) as exc:
        add("INPUT_UNREADABLE", f"Cannot parse canonical case: {type(exc).__name__}")
        finish()
        raise AssertionError("unreachable") from exc
    report.case_id = raw.get("case_id") if isinstance(raw.get("case_id"), str) else None
    clinical_raw = {key: value for key, value in raw.items() if key not in EDITOR_FIELDS}
    try:
        clinical = ClinicalCase.model_validate(clinical_raw)
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            location = error["loc"]
            kind = str(location[0]) if location else None
            row = clinical_raw.get(kind or "")
            if len(location) > 1 and isinstance(location[1], int) and isinstance(row, list):
                row = row[location[1]]
            record_id = row.get("id") if isinstance(row, dict) else None
            # Pydantic messages describe the constraint, without dumping clinical input.
            add(
                "STRUCTURE_" + error["type"].upper(),
                error["msg"],
                kind,
                record_id,
                ".".join(map(str, location)),
            )
        finish()
        raise AssertionError("unreachable") from exc
    if clinical.status != "ready":
        add("CASE_NOT_READY", "only ready clinical cases can be ingested", field="status")
    groups = {
        key: getattr(clinical, key)
        for key, value in clinical.model_dump().items()
        if isinstance(value, list)
    }
    report.counts = {key: len(value) for key, value in groups.items()}
    records: dict[str, Any] = {clinical.patient.id: clinical.patient}
    for kind, group in groups.items():
        for record in group:
            if record.id in records:
                add("DUPLICATE_ID", "duplicate canonical record ID", kind, record.id, "id")
            records[record.id] = record
    encounters = {r.id for r in clinical.encounters}
    documents = {r.id for r in clinical.documents}
    studies = {r.id for r in clinical.imaging_studies}
    observations = {r.id for r in clinical.observations}
    targets = {
        "encounter_id": encounters,
        "source_document_id": documents,
        "report_document_id": documents,
        "document_id": documents,
        "imaging_study_id": studies,
    }
    for kind, group in groups.items():
        for record in group:
            if getattr(record, "patient_id", clinical.patient.id) != clinical.patient.id:
                add(
                    "PATIENT_MISMATCH",
                    "patient_id does not match case patient",
                    kind,
                    record.id,
                    "patient_id",
                )
            for field, allowed in targets.items():
                reference = getattr(record, field, None)
                if reference is not None and reference not in allowed:
                    label = (
                        "source document"
                        if field in {"source_document_id", "report_document_id"}
                        else field
                    )
                    add(
                        "REFERENCE_MISSING",
                        f"{label} {reference} does not exist",
                        kind,
                        record.id,
                        field,
                    )
                elif reference is not None and field != "encounter_id":
                    target = records[reference]
                    left = getattr(record, "encounter_id", None)
                    right = getattr(target, "encounter_id", None)
                    if left and right and left != right:
                        add(
                            "CROSS_ENCOUNTER_SOURCE",
                            "Source belongs to another encounter; review",
                            kind,
                            record.id,
                            field,
                            "warning",
                        )
            links = getattr(record, "observation_ids", [])
            if len(set(links)) != len(links):
                add(
                    "DUPLICATE_LINK",
                    "duplicate observation link",
                    kind,
                    record.id,
                    "observation_ids",
                )
            for reference in links:
                if reference not in observations:
                    add(
                        "REFERENCE_MISSING",
                        f"observation {reference} does not exist",
                        kind,
                        record.id,
                        "observation_ids",
                    )
            metadata = getattr(record, "metadata", {})
            for dimension in ["width", "height"]:
                value = metadata.get(dimension)
                if value is not None and (type(value) is not int or value <= 0):
                    add(
                        "MEDIA_DIMENSION",
                        "Image dimensions must be positive integers",
                        kind,
                        record.id,
                        f"metadata.{dimension}",
                    )
            if kind == "medications" and record.dose is not None and record.dose < 0:
                add("NEGATIVE_DOSE", "Medication dose cannot be negative", kind, record.id, "dose")
            if kind == "imaging_studies" and record.performed_at and record.reported_at:
                if record.reported_at < record.performed_at:
                    add(
                        "IMAGING_INTERVAL",
                        "reported_at precedes performed_at",
                        kind,
                        record.id,
                        "reported_at",
                    )
            if kind == "documents" and record.event_at and record.authored_at:
                if record.authored_at < record.event_at:
                    add(
                        "DOCUMENT_CHRONOLOGY_REVIEW",
                        "Authored before clinical event; review",
                        kind,
                        record.id,
                        "authored_at",
                        "warning",
                    )
            if kind == "referrals" and record.ordered_at and record.appointment_at:
                if record.appointment_at < record.ordered_at:
                    add(
                        "REFERRAL_CHRONOLOGY_REVIEW",
                        "Appointment before order; review",
                        kind,
                        record.id,
                        "appointment_at",
                        "warning",
                    )
            for field, value in record.model_dump().items():
                if field.endswith("_at") and value is None:
                    add(
                        "TIME_UNKNOWN",
                        "Timestamp absent; no event time inferred",
                        kind,
                        record.id,
                        field,
                        "info",
                    )
                elif field.endswith("_at") and isinstance(value, str) and len(value) == 10:
                    add(
                        "DATE_PRECISION",
                        "Date-only value retained without midnight conversion",
                        kind,
                        record.id,
                        field,
                        "info",
                    )
    if clinical.updated_at < clinical.created_at:
        add("DATASET_INTERVAL", "updated_at precedes created_at", field="updated_at")
    if any(r.started_at.date() < clinical.patient.date_of_birth for r in clinical.encounters):
        add(
            "BIRTH_AFTER_ENCOUNTER",
            "Patient birth date follows an encounter",
            "patient",
            clinical.patient.id,
            "date_of_birth",
        )
    assets: dict[str, AssetInfo] = {}
    asset_records: list[Document | ImagingAsset] = [*clinical.documents, *clinical.imaging_assets]
    for record in asset_records:
        if record.storage_path:
            report.assets_checked += 1
            try:
                assets[record.id] = storage.inspect(
                    record.storage_path, clinical.case_id, record.mime_type
                )
            except ValueError as exc:
                add("ASSET_INVALID", str(exc), type(record).__name__, record.id, "storage_path")
    validate_manifest(path, source_bytes, clinical, assets, report)
    finish()
    return ValidatedCase(clinical, assets, report)
