"""Common envelopes and fail-closed validation of clinical source projections."""

from datetime import UTC, datetime

from app.core.provenance import digest
from app.hospital import schemas as dto
from app.hospital.errors import HospitalError
from app.schemas.investigation import SourceRecord, ToolResult

SOURCE_MODELS: dict[str, type[dto.ClinicalModel]] = {
    "patient": dto.PatientResponse,
    "encounter": dto.Encounter,
    "clinical_event": dto.ClinicalEvent,
    "observation": dto.Observation,
    "medication": dto.Medication,
    "document": dto.DocumentResponse,
    "imaging_study": dto.ImagingStudy,
    "imaging_asset": dto.ImagingAssetResponse,
    "referral": dto.Referral,
    "diagnostic_report": dto.DiagnosticReport,
    "diagnosis": dto.Diagnosis,
    "symptom": dto.Symptom,
}


def validate_source(record: SourceRecord, patient_id: str) -> None:
    if record.representation != "source":
        raise HospitalError("INVALID_SOURCE_REPRESENTATION", 422)
    SOURCE_MODELS[record.source.type].model_validate(record.data)
    if set(record.data.get("metadata", {})) - {"department", "width", "height", "synthetic_label"}:
        raise HospitalError("INVALID_SOURCE_METADATA", 422)
    owner = record.data.get("patient_id")
    if record.source.type == "patient":
        owner = record.source.id
    if owner is not None and owner != patient_id:
        raise HospitalError("PATIENT_SCOPE_VIOLATION", 403)
    if (
        record.data.get("id") != record.source.id
        or record.source_version < 1
        or digest(record.data) != record.source_hash
    ):
        raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)


def result_for(records: list[SourceRecord], total: int, offset: int = 0) -> ToolResult:
    more = offset + len(records) < total
    return ToolResult(
        status="partial" if more else "success" if records else "empty",
        records=records,
        source_refs=[r.source for r in records],
        total=total,
        has_more=more,
        retrieved_at=datetime.now(UTC),
    )


def validate_result(result: ToolResult, patient_id: str) -> None:
    if result.total < 0 or result.total < len(result.records):
        raise HospitalError("INVALID_TOOL_RESULT", 422)
    keys = [(r.source.type, r.source.id) for r in result.records]
    if len(set(keys)) != len(keys) or result.source_refs != [r.source for r in result.records]:
        raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)
    for record in result.records:
        if record.representation == "search_hit":
            dto.DocumentSearchHit.model_validate(record.data)
            if (
                record.source.type != "document"
                or record.data["id"] != record.source.id
                or record.source_version < 1
                or len(record.source_hash) != 64
                or record.representation_hash != digest(record.data)
            ):
                raise HospitalError("INVALID_SOURCE_PROVENANCE", 422)
        else:
            validate_source(record, patient_id)
