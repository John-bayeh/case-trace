"""Read clinical asset metadata, then release the DB before filesystem work."""

import asyncio
from pathlib import Path

from app.clinical.assets import AssetDescriptor as AssetDescriptor
from app.hospital.assets import AssetError, LocalAssetStorage
from app.hospital.errors import HospitalError
from app.hospital.repository import HospitalRepository
from app.hospital.schemas import ImagingAssetResponse
from app.models import hospital as db


class ClinicalAssetService:
    def __init__(self, repository: HospitalRepository):
        self.repository = repository

    async def metadata(
        self, patient_external_id: str, asset_id: str
    ) -> tuple[ImagingAssetResponse, int]:
        record = await self.repository.get(db.ImagingAsset, asset_id)
        if record is None:
            raise HospitalError()
        study = await self.repository.by_id(db.ImagingStudy, record.study_id)
        patient = await self.repository.get(db.Patient, patient_external_id)
        if study is None or patient is None or study.patient_id != patient.id:
            raise HospitalError()
        metadata = record.payload.get("metadata", {})
        return ImagingAssetResponse(
            id=record.external_id,
            imaging_study_id=study.external_id,
            asset_type=record.asset_kind,
            mime_type=record.payload["mime_type"],
            width=metadata.get("width"),
            height=metadata.get("height"),
            metadata=metadata,
        ), study.source_version

    async def describe(self, patient_id: object, asset: db.Asset | None) -> AssetDescriptor:
        if asset is None:
            raise HospitalError("ASSET_NOT_FOUND")
        patient = await self.repository.by_id(db.Patient, patient_id)
        if patient is None:
            raise HospitalError()
        dataset = await self.repository.dataset(patient)
        descriptor = AssetDescriptor(
            asset.external_id,
            dataset.case_id,
            asset.storage_key,
            asset.mime_type,
            asset.sha256,
            asset.byte_size,
        )
        await self.repository.release()
        return descriptor

    async def document(self, document_id: str) -> AssetDescriptor:
        document = await self.repository.get(db.ClinicalDocument, document_id)
        if document is None:
            raise HospitalError()
        version = await self.repository.document_version(document)
        asset = (
            await self.repository.asset(version.artifact_id)
            if version and version.artifact_id
            else None
        )
        return await self.describe(document.patient_id, asset)

    async def imaging(self, external_id: str) -> AssetDescriptor:
        record = await self.repository.get(db.ImagingAsset, external_id)
        if record is None:
            raise HospitalError()
        study = await self.repository.by_id(db.ImagingStudy, record.study_id)
        if study is None:
            raise HospitalError()
        return await self.describe(study.patient_id, await self.repository.asset(record.asset_id))

    async def images(
        self, study_id: str, limit: int, offset: int
    ) -> tuple[list[ImagingAssetResponse], int]:
        study = await self.repository.get(db.ImagingStudy, study_id)
        if study is None:
            raise HospitalError()
        records = await self.repository.study_assets(study)
        data = []
        for record in records[offset : offset + limit]:
            raw = record.payload
            metadata = raw.get("metadata", {})
            data.append(
                ImagingAssetResponse(
                    id=record.external_id,
                    imaging_study_id=study_id,
                    asset_type=record.asset_kind,
                    mime_type=raw["mime_type"],
                    width=metadata.get("width"),
                    height=metadata.get("height"),
                    metadata=metadata,
                )
            )
        return data, len(records)


async def verified_asset_path(root: Path, asset: AssetDescriptor) -> Path:
    storage = LocalAssetStorage(root)
    try:
        info = await asyncio.to_thread(
            storage.inspect, asset.storage_key, asset.case_id, asset.mime_type
        )
        if info.sha256 != asset.sha256 or info.byte_size != asset.byte_size:
            raise HospitalError("ASSET_INTEGRITY_ERROR", 409)
        return storage.resolve(asset.storage_key, asset.case_id)
    except AssetError as exc:
        raise HospitalError("ASSET_UNAVAILABLE") from exc


class LocalAssetReader:
    def __init__(self, root: Path):
        self.root = root

    async def verified_path(self, asset: AssetDescriptor) -> Path:
        return await verified_asset_path(self.root, asset)
