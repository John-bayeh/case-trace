"""Read-only hospital repositories. No raw case/evaluation filesystem access."""

from typing import Any, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import hospital as db
from app.models.base import Base

T = TypeVar("T", bound=Base)


class HospitalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_id(self, model: type[T], identifier: Any) -> T | None:
        return await self.session.get(model, identifier)

    async def release(self) -> None:
        await self.session.rollback()

    async def get(self, model: type[T], external_id: str) -> T | None:
        return cast(
            T | None,
            await self.session.scalar(
                select(model).where(cast(Any, model).external_id == external_id)
            ),
        )

    async def patients(self) -> list[db.Patient]:
        return list(await self.session.scalars(select(db.Patient).order_by(db.Patient.external_id)))

    async def datasets(self) -> list[db.CaseDataset]:
        return list(await self.session.scalars(select(db.CaseDataset)))

    async def source_versions(self, model: type[T], identifiers: list[str]) -> dict[str, int]:
        rows = await self.session.execute(
            select(cast(Any, model).external_id, cast(Any, model).source_version).where(
                cast(Any, model).external_id.in_(identifiers)
            )
        )
        return {identifier: version for identifier, version in rows}

    async def for_patient(self, model: type[T], patient: db.Patient) -> list[T]:
        return list(
            await self.session.scalars(
                select(model).where(cast(Any, model).patient_id == patient.id)
            )
        )

    async def dataset(self, patient: db.Patient) -> db.CaseDataset:
        dataset = await self.session.get(db.CaseDataset, patient.dataset_id)
        assert dataset is not None
        return dataset

    async def document_version(self, document: db.ClinicalDocument) -> db.DocumentVersion | None:
        if document.current_version_id is None:
            return None
        result = await self.session.scalar(
            select(db.DocumentVersion).where(
                db.DocumentVersion.id == document.current_version_id,
                db.DocumentVersion.document_id == document.id,
            )
        )

        return result

    async def asset(self, asset_id: Any) -> db.Asset | None:
        return await self.session.get(db.Asset, asset_id)

    async def study_assets(self, study: db.ImagingStudy) -> list[db.ImagingAsset]:
        return list(
            await self.session.scalars(
                select(db.ImagingAsset)
                .where(db.ImagingAsset.study_id == study.id)
                .order_by(db.ImagingAsset.external_id)
            )
        )
