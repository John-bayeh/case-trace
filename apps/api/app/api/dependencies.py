from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.hospital.asset_service import ClinicalAssetService
from app.hospital.repository import HospitalRepository
from app.hospital.service import ClinicalRecordService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


async def clinical_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClinicalRecordService:
    return ClinicalRecordService(HospitalRepository(session))


async def asset_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClinicalAssetService:
    return ClinicalAssetService(HospitalRepository(session))
