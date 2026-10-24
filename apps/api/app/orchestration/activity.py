"""Durable stage, agent, tool and event writes."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.core.provenance import now
from app.models import investigation as db
from app.orchestration.persistence import InvestigationPersistence
from app.orchestration.state import RunConflict


class InvestigationActivity:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def record(self, public_id: str, event: str, payload: dict[str, Any]) -> None:
        async with self.persistence.mutation(public_id, event, payload):
            pass

    async def stage(
        self, public_id: str, key: str, done: bool = False, outcome: str = "completed"
    ) -> None:
        if outcome not in {"completed", "failed", "skipped"}:
            raise ValueError("INVALID_STAGE_OUTCOME")
        async with self.persistence.mutation(
            public_id,
            f"stage.{outcome}" if done else "stage.started",
            {
                "stage": key,
            },
        ) as (session, run):
            if done:
                row = await session.scalar(
                    select(db.InvestigationStage).where(
                        db.InvestigationStage.investigation_id == run.id,
                        db.InvestigationStage.stage_key == key,
                    )
                )
                if row is None or row.status != "running":
                    raise RunConflict()
                row.status, row.ended_at = outcome, now()
            else:
                session.add(
                    db.InvestigationStage(
                        investigation_id=run.id,
                        stage_key=key,
                        status="running",
                        started_at=now(),
                    )
                )
            run.context = {
                **run.context,
                "current_stage": key,
                "completed_stages": run.context["completed_stages"] + int(done),
            }

    async def agent_start(self, public_id: str, name: str) -> UUID:
        execution_id = uuid4()
        async with self.persistence.mutation(
            public_id,
            "agent.started",
            {
                "agent": name,
                "agent_run_id": str(execution_id),
            },
        ) as (session, run):
            attempt = (
                await session.scalar(
                    select(func.max(db.AgentExecution.attempt)).where(
                        db.AgentExecution.investigation_id == run.id,
                        db.AgentExecution.agent_key == name,
                    )
                )
                or 0
            ) + 1
            row = db.AgentExecution(
                id=execution_id,
                investigation_id=run.id,
                agent_key=name,
                attempt=attempt,
                status="running",
                started_at=now(),
            )
            session.add(row)
            await session.flush()
            return row.id

    async def agent_end(
        self,
        public_id: str,
        agent_id: UUID,
        error: str | None = None,
    ) -> None:
        payload = {"agent_run_id": str(agent_id), "error_code": error}
        async with self.persistence.mutation(
            public_id,
            "agent.failed" if error else "agent.completed",
            payload,
        ) as (session, run):
            row = await session.get(db.AgentExecution, agent_id)
            if row is None or row.investigation_id != run.id or row.status != "running":
                raise RunConflict()
            row.status, row.ended_at = "failed" if error else "completed", now()
            payload["agent"] = row.agent_key
            row.task_summary = {"error_code": error} if error else {}

    async def tool_start(
        self,
        public_id: str,
        agent_id: UUID,
        name: str,
        args: dict[str, Any],
        agent_name: str,
    ) -> UUID:
        call_id = uuid4()
        async with self.persistence.mutation(
            public_id,
            "tool.started",
            {
                "agent_run_id": str(agent_id),
                "agent": agent_name,
                "tool": name,
                "tool_execution_id": str(call_id),
            },
        ) as (session, run):
            actor = await session.get(db.AgentExecution, agent_id)
            if (
                run.status != "running"
                or actor is None
                or actor.investigation_id != run.id
                or actor.status != "running"
                or actor.agent_key != agent_name
            ):
                raise RunConflict()
            row = db.ToolCall(
                id=call_id,
                investigation_id=run.id,
                agent_execution_id=agent_id,
                tool_name=name,
                sanitized_args=args,
                status="running",
                started_at=now(),
            )
            session.add(row)
            await session.flush()
            return row.id

    async def tool_end(
        self,
        public_id: str,
        call_id: UUID,
        refs: list[dict[str, Any]],
        error: str | None = None,
    ) -> None:
        payload = {
            "tool_execution_id": str(call_id),
            "source_refs": refs,
            "record_count": len(refs),
            "error_code": error,
        }
        async with self.persistence.mutation(
            public_id,
            "tool.failed" if error else "tool.completed",
            payload,
        ) as (session, run):
            row = await session.get(db.ToolCall, call_id)
            if row is None or row.investigation_id != run.id:
                raise RunConflict()
            row.status = "failed" if error else "succeeded"
            payload["tool"] = row.tool_name
            payload["agent_run_id"] = str(row.agent_execution_id)
            row.completed_at, row.error_code, row.result_refs = now(), error, refs
            row.duration_ms = int((row.completed_at - row.started_at).total_seconds() * 1000)
