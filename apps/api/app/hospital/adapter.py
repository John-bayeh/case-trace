"""Local read-only adapter; materialize DTOs and release sessions before asset IO."""

from typing import Any

from pydantic import BaseModel

from app.clinical.assets import AssetReader
from app.core.database import Database
from app.core.provenance import digest
from app.hospital.asset_service import ClinicalAssetService
from app.hospital.repository import HospitalRepository
from app.hospital.schemas import DocumentSearchHit
from app.hospital.service import RESOURCES, ClinicalRecordService, HospitalError
from app.schemas.investigation import SourceRecord, SourceRef, SourceType

RESOURCE_TYPES = {
    "encounter": "encounters",
    "clinical_event": "clinical-events",
    "observation": "observations",
    "medication": "medications",
    "document": "documents",
    "imaging_study": "imaging-studies",
    "referral": "referrals",
    "diagnostic_report": "diagnostic-reports",
    "diagnosis": "diagnoses",
    "symptom": "symptoms",
}


class SimulatedHospitalAdapter:
    def __init__(self, database: Database, assets: AssetReader):
        self.database, self.assets = database, assets

    async def resolve(self, patient_id: str, source: SourceRef) -> SourceRecord:
        async with self.database.session() as session:
            repo = HospitalRepository(session)
            service = ClinicalRecordService(repo)
            patient = await service.patient(patient_id)
            if source.type == "imaging_asset":
                metadata, version = await ClinicalAssetService(repo).metadata(patient_id, source.id)
                data = metadata.model_dump(mode="json")
                return SourceRecord(
                    source=source, source_version=version, source_hash=digest(data), data=data
                )
            row: Any
            dto: BaseModel
            if source.type == "patient":
                if source.id != patient_id:
                    raise HospitalError()
                row, dto = patient, await service.patient_dto(patient)
            else:
                resource = RESOURCE_TYPES[source.type]
                row = await repo.get(RESOURCES[resource][1], source.id)
                if row is None or row.patient_id != patient.id:
                    raise HospitalError()
                dto = await service.project(resource, row)
            data = dto.model_dump(mode="json")
            result = SourceRecord(
                source=source,
                source_version=row.source_version,
                source_hash=digest(data),
                data=data,
            )
            descriptor = None
            if source.type == "document" and data.get("has_asset"):
                descriptor = await ClinicalAssetService(repo).document(source.id)
        if descriptor:
            await self.assets.verified_path(descriptor)
        return result

    async def records(
        self, source_type: SourceType, patient_id: str, filters: dict[str, Any]
    ) -> tuple[list[SourceRecord], int]:
        async with self.database.session() as session:
            repo = HospitalRepository(session)
            service = ClinicalRecordService(repo)
            rows, total = await service.list_records(
                RESOURCE_TYPES[source_type], patient_id, filters
            )
            # Reuse projected DTOs: do not reopen a session and project every row twice.
            records = []
            descriptors = []
            versions = await repo.source_versions(
                RESOURCES[RESOURCE_TYPES[source_type]][1],
                [str(dto.model_dump()["id"]) for dto in rows],
            )
            for dto in rows:
                data = dto.model_dump(mode="json")
                if data["id"] not in versions:
                    raise HospitalError()
                records.append(
                    SourceRecord(
                        source=SourceRef(type=source_type, id=data["id"]),
                        source_version=versions[data["id"]],
                        source_hash=digest(data),
                        data=data,
                    )
                )
                if source_type == "document" and data.get("has_asset"):
                    descriptors.append(await ClinicalAssetService(repo).document(data["id"]))
        for descriptor in descriptors:
            await self.assets.verified_path(descriptor)
        return records, total

    async def search_documents(
        self, patient_id: str, query: str, filters: dict[str, Any]
    ) -> tuple[list[DocumentSearchHit], int]:
        async with self.database.session() as session:
            service = ClinicalRecordService(HospitalRepository(session))
            return await service.search_documents(patient_id, query, filters)
