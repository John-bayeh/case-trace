"""The only capability exposed to specialists."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol
from uuid import UUID

from app.schemas.investigation import ToolResult


class ToolExecutor(Protocol):
    @property
    def patient_id(self) -> str: ...

    async def execute(
        self, agent: str, agent_id: UUID, name: str, raw: dict[str, Any]
    ) -> ToolResult: ...


class ScopedToolExecutor:
    """Expose execution only; specialists receive no registry/store/source members."""

    def __init__(
        self,
        patient_id: str,
        execute: Callable[[str, UUID, str, dict[str, Any]], Awaitable[ToolResult]],
    ):
        self.patient_id = patient_id
        self._execute = execute

    async def execute(
        self, agent: str, agent_id: UUID, name: str, raw: dict[str, Any]
    ) -> ToolResult:
        return await self._execute(agent, agent_id, name, raw)
