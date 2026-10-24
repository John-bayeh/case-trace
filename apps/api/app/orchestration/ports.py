"""Runtime persistence and audit capabilities, independent of ORM implementations."""

from typing import Any, Protocol
from uuid import UUID

from app.schemas.investigation import ActivityEvent, Finding, Report


class ToolAudit(Protocol):
    async def record(self, public_id: str, event: str, payload: dict[str, Any]) -> None: ...

    async def tool_start(
        self,
        public_id: str,
        agent_id: UUID,
        name: str,
        args: dict[str, Any],
        agent_name: str,
    ) -> UUID: ...

    async def tool_end(
        self,
        public_id: str,
        call_id: UUID,
        refs: list[dict[str, Any]],
        error: str | None = None,
    ) -> None: ...


class InvestigationRuntime(ToolAudit, Protocol):
    async def transition(self, public_id: str, target: str, reason: str) -> None: ...

    async def record(self, public_id: str, event: str, payload: dict[str, Any]) -> None: ...

    async def stage(
        self, public_id: str, key: str, done: bool = False, outcome: str = "completed"
    ) -> None: ...

    async def context(self, public_id: str, **values: Any) -> None: ...

    async def agent_start(self, public_id: str, name: str) -> UUID: ...

    async def agent_end(
        self,
        public_id: str,
        agent_id: UUID,
        error: str | None = None,
    ) -> None: ...

    async def save_finding(self, public_id: str, finding: Finding) -> None: ...

    async def finalize(self, public_id: str, report: Report) -> None: ...

    async def snapshot(self, public_id: str) -> dict[str, Any]: ...

    async def events(self, public_id: str, after: int, limit: int = 100) -> list[ActivityEvent]: ...

    async def findings(self, public_id: str) -> list[Finding]: ...

    async def report(self, public_id: str) -> Report: ...
