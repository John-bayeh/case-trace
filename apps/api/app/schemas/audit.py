"""Allowlisted public tool audit projection."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.investigation import SourceRef


class ToolAudit(BaseModel):
    id: str
    agent_run_id: str
    agent: str
    attempt: int
    tool: str
    status: str
    arguments: dict[str, str | int | float | bool | None]
    source_refs: list[SourceRef]
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    error_code: str | None


class ToolAuditPage(BaseModel):
    investigation_id: str
    items: list[ToolAudit]
    total: int
    limit: int
    offset: int
