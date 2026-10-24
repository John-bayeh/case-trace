"""Investigation application facade over focused persistence collaborators.

All collaborators share one writer/CAS boundary. Existing callers retain the
supported store API while query, activity and lifecycle ownership are explicit.
"""

from typing import Any
from uuid import UUID

from app.core.database import Database
from app.orchestration.activity import InvestigationActivity
from app.orchestration.commands import InvestigationCommands
from app.orchestration.findings import FindingRepository
from app.orchestration.persistence import InvestigationPersistence
from app.orchestration.queries import InvestigationQueries
from app.orchestration.recovery import InvestigationRecovery
from app.orchestration.state import TERMINAL as TERMINAL
from app.orchestration.state import RunConflict as RunConflict
from app.schemas.investigation import ActivityEvent, CreateInvestigation, Finding, Report


class InvestigationStore:
    def __init__(self, database: Database):
        self.persistence = InvestigationPersistence(database)
        self.database = database
        self.commands = InvestigationCommands(self.persistence)
        self.activity = InvestigationActivity(self.persistence)
        self.findings_repository = FindingRepository(self.persistence)
        self.queries = InvestigationQueries(self.persistence)
        self.recovery_repository = InvestigationRecovery(self.persistence)

    async def create(
        self,
        request: CreateInvestigation,
        key: str | None,
    ) -> tuple[str, bool]:
        return await self.commands.create(request, key)

    async def transition(self, public_id: str, target: str, reason: str) -> None:
        return await self.commands.transition(public_id, target, reason)

    async def record(self, public_id: str, event: str, payload: dict[str, Any]) -> None:
        return await self.activity.record(public_id, event, payload)

    async def stage(
        self, public_id: str, key: str, done: bool = False, outcome: str = "completed"
    ) -> None:
        return await self.activity.stage(public_id, key, done, outcome)

    async def context(self, public_id: str, **values: Any) -> None:
        return await self.commands.context(public_id, **values)

    async def agent_start(self, public_id: str, name: str) -> UUID:
        return await self.activity.agent_start(public_id, name)

    async def agent_end(
        self,
        public_id: str,
        agent_id: UUID,
        error: str | None = None,
    ) -> None:
        return await self.activity.agent_end(public_id, agent_id, error)

    async def tool_start(
        self,
        public_id: str,
        agent_id: UUID,
        name: str,
        args: dict[str, Any],
        agent_name: str,
    ) -> UUID:
        return await self.activity.tool_start(public_id, agent_id, name, args, agent_name)

    async def tool_end(
        self,
        public_id: str,
        call_id: UUID,
        refs: list[dict[str, Any]],
        error: str | None = None,
    ) -> None:
        return await self.activity.tool_end(public_id, call_id, refs, error)

    async def save_finding(self, public_id: str, finding: Finding) -> None:
        return await self.findings_repository.save_finding(public_id, finding)

    async def finalize(self, public_id: str, report: Report) -> None:
        return await self.commands.finalize(public_id, report)

    async def snapshot(self, public_id: str) -> dict[str, Any]:
        return await self.queries.snapshot(public_id)

    async def events(self, public_id: str, after: int, limit: int = 100) -> list[ActivityEvent]:
        return await self.queries.events(public_id, after, limit)

    async def findings(self, public_id: str) -> list[Finding]:
        return await self.queries.findings(public_id)

    async def report(self, public_id: str) -> Report:
        return await self.queries.report(public_id)

    async def recover(self) -> None:
        return await self.recovery_repository.recover()
