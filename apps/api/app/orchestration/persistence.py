"""The single serialized transaction boundary shared by all persistence collaborators."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Database
from app.core.provenance import now
from app.hospital.errors import HospitalError
from app.models import investigation as db
from app.orchestration.state import TERMINAL, RunConflict


class InvestigationPersistence:
    def __init__(self, database: Database):
        self.database = database
        self.lock = asyncio.Lock()

    async def find(self, session: AsyncSession, public_id: str) -> db.Investigation:
        run = await session.scalar(
            select(db.Investigation).where(
                db.Investigation.external_id == public_id,
            )
        )
        if run is None:
            raise HospitalError("INVESTIGATION_NOT_FOUND")
        return run

    @asynccontextmanager
    async def mutation(
        self,
        public_id: str,
        event: str,
        payload: dict[str, Any],
        *,
        terminal: bool = False,
    ) -> AsyncIterator[tuple[AsyncSession, db.Investigation]]:
        async with self.lock, self.database.session() as session, session.begin():
            run = await self.find(session, public_id)
            if not terminal and run.status in TERMINAL:
                raise RunConflict()
            old_version, old_status = run.version, run.status
            yield session, run
            # The explicit CAS remains authoritative even with the process-local lock.
            with session.no_autoflush:
                result = await session.execute(
                    update(db.Investigation)
                    .where(
                        db.Investigation.id == run.id,
                        db.Investigation.version == old_version,
                        db.Investigation.status == old_status,
                    )
                    .values(version=old_version + 1)
                    .execution_options(synchronize_session=False)
                )
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise RunConflict()
            session.add(
                db.InvestigationEvent(
                    investigation_id=run.id,
                    sequence=old_version + 1,
                    event_type=event,
                    payload=payload,
                    occurred_at=now(),
                )
            )
