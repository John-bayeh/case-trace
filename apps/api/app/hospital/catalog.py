"""Neutral catalog projections; maintenance readiness never becomes agent context."""

import asyncio
import re

from pydantic import BaseModel

from app.core.config import Settings
from app.hospital.assets import LocalAssetStorage
from app.hospital.discovery import discover_case
from app.hospital.service import RESOURCES, ClinicalRecordService


class CaseOverview(BaseModel):
    case_id: str
    version: str | None = None
    patient_id: str | None = None
    display_name: str | None = None
    status: str
    imported: bool = False
    dataset_status: str | None = None
    counts: dict[str, int] = {}
    modalities: list[str] = []
    latest_encounter_at: str | None = None


class CaseCatalog:
    def __init__(self, service: ClinicalRecordService, settings: Settings):
        self.service = service
        self.settings = settings

    async def items(self, case_id: str | None = None) -> list[CaseOverview]:
        repo = self.service.repository
        datasets = await repo.datasets()
        fingerprints = {(d.case_id, d.dataset_version): d.seed_hash for d in datasets}
        imported: dict[str, CaseOverview] = {}
        for patient in await repo.patients():
            dataset = await repo.dataset(patient)
            if case_id and dataset.case_id != case_id:
                continue
            counts = {}
            modalities: set[str] = set()
            latest = None
            for resource, (_, model, _) in RESOURCES.items():
                rows = await repo.for_patient(model, patient)
                counts[resource.replace("-", "_")] = len(rows)
                if resource == "documents":
                    modalities.update(row.payload["mime_type"] for row in rows)
                if resource == "imaging-studies":
                    modalities.update(row.payload["modality"] for row in rows)
                if resource == "encounters" and rows:
                    latest = max(rows, key=lambda row: row.started_at).payload["started_at"]
            imported[dataset.case_id] = CaseOverview(
                case_id=dataset.case_id,
                version=dataset.dataset_version,
                patient_id=patient.external_id,
                display_name=patient.display_name,
                status="imported",
                imported=True,
                dataset_status=dataset.status,
                counts=counts,
                modalities=sorted(modalities),
                latest_encounter_at=latest,
            )
        # Filesystem validation/hashing must run without an open read transaction.
        await repo.release()
        if self.settings.app_env != "production":
            root = self.settings.casetrace_root / "data" / "cases"

            def readiness() -> dict[str, dict[str, object]]:
                names = (
                    [case_id]
                    if case_id
                    else sorted(
                        p.name
                        for p in root.iterdir()
                        if p.is_dir()
                        and not p.is_symlink()
                        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", p.name)
                    )
                    if root.is_dir()
                    else []
                )
                return {
                    name: {"case_id": name, "status": "invalid"}
                    if (root / name).is_symlink()
                    else discover_case(
                        root,
                        name,
                        LocalAssetStorage(self.settings.resolved_asset_path),
                        fingerprints,
                    )
                    for name in names
                }

            discovered = await asyncio.to_thread(readiness)
            for name, item in discovered.items():
                status = str(item["status"])
                if name in imported:
                    # Imported records remain browsable even when maintenance inputs are absent.
                    if status not in {"not_present", "imported"}:
                        imported[name].status = status
                else:
                    imported[name] = CaseOverview.model_validate(
                        {
                            k: v
                            for k, v in item.items()
                            if k
                            in {
                                "case_id",
                                "version",
                                "patient_id",
                                "status",
                                "counts",
                                "display_name",
                                "dataset_status",
                                "modalities",
                                "latest_encounter_at",
                            }
                        }
                    )
        return sorted(imported.values(), key=lambda item: item.case_id)
