"""Maintenance case readiness, deliberately outside runtime clinical retrieval."""

from collections.abc import Mapping
from pathlib import Path

from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import import_fingerprint
from app.hospital.validation import CaseValidationError, validate_case


def discover_case(
    case_root: Path,
    case_id: str,
    storage: LocalAssetStorage,
    imported: Mapping[tuple[str, str], str],
) -> dict[str, object]:
    """Imported readiness requires a matching persisted fingerprint, never a guess."""
    from pydantic import TypeAdapter

    from app.hospital.schemas import Identifier

    TypeAdapter(Identifier).validate_python(case_id)
    path = case_root / case_id / "case.json"
    if not path.is_file():
        return {"case_id": case_id, "status": "not_present"}
    try:
        validated = validate_case(path, storage)
    except CaseValidationError as exc:
        diagnostics = exc.report.diagnostics if exc.report else []
        missing = any(d.code == "ASSET_INVALID" and "missing" in d.description for d in diagnostics)
        return {
            "case_id": case_id,
            "status": "missing_assets" if missing else "invalid",
            "validation": exc.report.as_dict() if exc.report else None,
        }
    case = validated.clinical
    if case.case_id != case_id:
        return {"case_id": case_id, "status": "invalid", "code": "CASE_DIRECTORY_MISMATCH"}
    existing = imported.get((case.case_id, case.version))
    fingerprint = import_fingerprint(validated)
    status = "available_not_imported"
    if existing is not None:
        status = "imported" if existing == fingerprint else "source_conflict"
    return {
        "case_id": case.case_id,
        "version": case.version,
        "patient_id": case.patient.id,
        "display_name": case.patient.display_name,
        "dataset_status": case.status,
        "modalities": sorted(
            {d.mime_type for d in case.documents} | {s.modality for s in case.imaging_studies}
        ),
        "latest_encounter_at": max(e.started_at for e in case.encounters).isoformat()
        if case.encounters
        else None,
        "status": status,
        "source_hash": fingerprint,
        "counts": validated.report.counts if validated.report else {},
        "assets": len(validated.assets),
    }
