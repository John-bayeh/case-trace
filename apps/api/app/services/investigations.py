"""Investigation creation use case; HTTP owns validation and serialization."""

from typing import Protocol

from app.orchestration.store import InvestigationStore
from app.schemas.investigation import CreateInvestigation, CreationResponse


class Scheduler(Protocol):
    def schedule(self, public_id: str) -> None: ...


class InvestigationService:
    def __init__(self, store: InvestigationStore, scheduler: Scheduler):
        self.store, self.scheduler = store, scheduler

    async def create(
        self, body: CreateInvestigation, idempotency_key: str | None
    ) -> CreationResponse:
        public_id, created = await self.store.create(body, idempotency_key)
        if created:
            self.scheduler.schedule(public_id)
        state = await self.store.snapshot(public_id)
        return CreationResponse(
            investigation_id=public_id,
            status=state["status"],
            patient_id=state["patient_id"],
            created_at=state["created_at"],
        )
