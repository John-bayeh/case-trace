"""Maintenance-only frozen manifest checks; no evaluator dependency."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from app.hospital.assets import AssetInfo
from app.hospital.diagnostics import Diagnostic, ValidationReport
from app.hospital.schemas import ClinicalCase, Document, ImagingAsset


def validate_manifest(
    path: Path,
    source_bytes: bytes,
    clinical: ClinicalCase,
    assets: dict[str, AssetInfo],
    report: ValidationReport,
) -> None:
    """Verify the existing public integrity envelope without reading evaluator keys."""
    manifest_path = path.with_name("manifest.json")

    def issue(
        code: str,
        message: str,
        record_id: str | None = None,
        field: str | None = None,
        severity: Literal["error", "warning", "info"] = "error",
    ) -> None:
        report.diagnostics.append(
            Diagnostic(
                clinical.case_id,
                str(manifest_path),
                "manifest",
                record_id,
                field,
                code,
                message,
                severity,
            )
        )

    if not manifest_path.exists():
        issue(
            "MANIFEST_ABSENT",
            "No manifest; asset signatures checked, no frozen checksum baseline",
            severity="warning",
        )
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
        for field, expected in {
            "case_id": clinical.case_id,
            "version": clinical.version,
            "case_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "counts": report.counts,
        }.items():
            if manifest.get(field) != expected:
                issue("MANIFEST_MISMATCH", f"Manifest {field} mismatch", field=field)
        entries = manifest.get("assets")
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            raise ValueError("manifest assets must be objects")
        ids = [entry.get("id") for entry in entries]
        asset_records: list[Document | ImagingAsset] = [
            *clinical.documents,
            *clinical.imaging_assets,
        ]
        expected_records = {r.id: r for r in asset_records if r.storage_path}
        clinical_records = [r for key in report.counts for r in getattr(clinical, key)]
        if any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("manifest asset IDs must be unique strings")
        if set(ids) != set(expected_records):
            issue("MANIFEST_ASSET_REGISTRY", "Manifest asset registry mismatch", field="assets")
        for entry in entries:
            record = expected_records.get(entry["id"])
            info = assets.get(entry["id"])
            if record is None or info is None:
                continue
            for field, asset_expected in {
                "sha256": info.sha256,
                "byte_size": info.byte_size,
                "storage_path": info.key,
                "mime_type": record.mime_type,
                "patient_id": clinical.patient.id,
                "source_version": 1,
            }.items():
                if entry.get(field) != asset_expected:
                    issue("MANIFEST_ASSET_MISMATCH", f"Asset {field} mismatch", record.id, field)
            # Optional metadata remains absent when the canonical source lacks it.
            if hasattr(record, "encounter_id") and entry.get("encounter_id") != record.encounter_id:
                issue(
                    "MANIFEST_SOURCE_MISMATCH",
                    "Asset encounter mismatch",
                    record.id,
                    "encounter_id",
                )
            if (
                isinstance(record, ImagingAsset)
                and entry.get("imaging_study_id") != record.imaging_study_id
            ):
                issue(
                    "MANIFEST_SOURCE_MISMATCH",
                    "Asset imaging study mismatch",
                    record.id,
                    "imaging_study_id",
                )
            if "linked_record_ids" in entry:
                expected_links = {
                    r.id
                    for r in clinical_records
                    if any(
                        getattr(r, field, None) == record.id
                        for field in ["source_document_id", "report_document_id", "document_id"]
                    )
                }
                links = entry["linked_record_ids"]
                if (
                    not isinstance(links, list)
                    or any(not isinstance(i, str) for i in links)
                    or len(set(links)) != len(links)
                    or set(links) != expected_links
                ):
                    issue(
                        "MANIFEST_LINK_MISMATCH",
                        "Asset source-to-record links mismatch",
                        record.id,
                        "linked_record_ids",
                    )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issue("MANIFEST_INVALID", f"Invalid manifest: {type(exc).__name__}")
