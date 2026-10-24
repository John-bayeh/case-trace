"""Read-only frontend projections over committed state."""

from typing import Any

from sqlalchemy import func, select

from app.hospital.errors import HospitalError
from app.models import investigation as db
from app.models.hospital import CaseDataset, Patient
from app.orchestration.narration import project
from app.orchestration.persistence import InvestigationPersistence
from app.schemas.audit import ToolAudit, ToolAuditPage
from app.schemas.investigation import (
    ActivityEvent,
    Finding,
    InvestigationHistory,
    InvestigationHistoryItem,
    Report,
)


class InvestigationQueries:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def tools(self, public_id: str, limit: int, offset: int) -> ToolAuditPage:
        allowed = {
            "filter_fingerprint",
            "patient_id",
            "encounter_id",
            "document_id",
            "observation_id",
            "medication_id",
            "record_id",
            "study_id",
            "report_id",
            "source_id",
            "source_type",
            "test_code",
            "from_date",
            "to_date",
            "timestamp_field",
            "category",
            "status",
            "limit",
            "offset",
        }
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            query = (
                select(db.ToolCall, db.AgentExecution)
                .join(db.AgentExecution, db.ToolCall.agent_execution_id == db.AgentExecution.id)
                .where(
                    db.ToolCall.investigation_id == run.id,
                    db.AgentExecution.investigation_id == run.id,
                )
            )
            total = await session.scalar(select(func.count()).select_from(query.subquery()))
            rows = await session.execute(
                query.order_by(db.ToolCall.started_at, db.ToolCall.id).limit(limit).offset(offset)
            )
            return ToolAuditPage(
                investigation_id=public_id,
                total=total or 0,
                limit=limit,
                offset=offset,
                items=[
                    ToolAudit(
                        id=str(call.id),
                        agent_run_id=str(agent.id),
                        agent=agent.agent_key,
                        attempt=agent.attempt,
                        tool=call.tool_name,
                        status=call.status,
                        arguments={
                            k: v
                            for k, v in call.sanitized_args.items()
                            if k in allowed
                            and (v is None or isinstance(v, (str, int, float, bool)))
                        },
                        source_refs=call.result_refs,
                        started_at=call.started_at,
                        completed_at=call.completed_at,
                        duration_ms=call.duration_ms,
                        error_code=call.error_code,
                    )
                    for call, agent in rows
                ],
            )

    async def history(
        self,
        patient_id: str | None,
        case_id: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> InvestigationHistory:
        async with self.persistence.database.session() as session:
            query = (
                select(db.Investigation, Patient.external_id, CaseDataset.case_id)
                .join(Patient, Patient.id == db.Investigation.patient_id)
                .join(CaseDataset, CaseDataset.id == db.Investigation.dataset_id)
            )
            if patient_id:
                query = query.where(Patient.external_id == patient_id)
            if case_id:
                query = query.where(CaseDataset.case_id == case_id)
            if status:
                query = query.where(db.Investigation.status == status)
            total = await session.scalar(select(func.count()).select_from(query.subquery()))
            rows = await session.execute(
                query.order_by(db.Investigation.created_at.desc(), db.Investigation.external_id)
                .limit(limit)
                .offset(offset)
            )
            return InvestigationHistory(
                items=[
                    InvestigationHistoryItem(
                        id=run.external_id,
                        patient_id=patient,
                        case_id=case,
                        objective=run.question,
                        status=run.status,
                        created_at=run.created_at,
                        started_at=run.started_at,
                        completed_at=run.ended_at,
                        current_stage=run.context.get("current_stage"),
                    )
                    for run, patient, case in rows
                ],
                total=total or 0,
                limit=limit,
                offset=offset,
            )

    async def snapshot(self, public_id: str) -> dict[str, Any]:
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            agents = list(
                await session.scalars(
                    select(db.AgentExecution)
                    .where(
                        db.AgentExecution.investigation_id == run.id,
                    )
                    .order_by(db.AgentExecution.started_at)
                )
            )
            findings = list(
                await session.scalars(
                    select(db.Finding).where(
                        db.Finding.investigation_id == run.id,
                    )
                )
            )
            # Repeated specialist tasks retain all audit rows, with one public role summary.
            summaries: dict[str, dict[str, Any]] = {}
            for agent in agents:
                previous = summaries.get(agent.agent_key)
                summaries[agent.agent_key] = {
                    "name": agent.agent_key,
                    "status": agent.status,
                    "started_at": previous["started_at"] if previous else agent.started_at,
                    "completed_at": agent.ended_at,
                }
            for agent in agents:
                if agent.status == "running":
                    summaries[agent.agent_key]["status"] = "running"
                    summaries[agent.agent_key]["completed_at"] = None
            return {
                "id": public_id,
                "patient_id": run.context["patient_id"],
                "case_id": run.context["case_id"],
                "objective": run.question,
                "status": run.status,
                "created_at": run.created_at,
                "started_at": run.started_at,
                "completed_at": run.ended_at,
                "version": run.version,
                "progress": {
                    "current_stage": run.context["current_stage"],
                    "completed_stages": run.context["completed_stages"],
                    "total_stages": 5,
                    "percent": 20 * run.context["completed_stages"],
                },
                "agents": list(summaries.values()),
                "finding_summary": {
                    s: sum(f.status == s for f in findings)
                    for s in ["proposed", "verified", "rejected", "unresolved"]
                },
                **{k: run.context.get(k, []) for k in ["timeline", "hypotheses", "limitations"]},
            }

    async def events(self, public_id: str, after: int, limit: int = 100) -> list[ActivityEvent]:
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            rows = await session.scalars(
                select(db.InvestigationEvent)
                .where(
                    db.InvestigationEvent.investigation_id == run.id,
                    db.InvestigationEvent.sequence > after,
                )
                .order_by(db.InvestigationEvent.sequence)
                .limit(limit)
            )
            return [
                ActivityEvent(
                    id=f"EVT-{row.id.hex}",
                    investigation_id=public_id,
                    sequence=row.sequence,
                    type=row.event_type,
                    timestamp=row.occurred_at,
                    payload=row.payload,
                    message=project(row.event_type, row.payload)[0],
                    execution_status=project(row.event_type, row.payload)[1],
                )
                for row in rows
            ]

    async def findings(self, public_id: str) -> list[Finding]:
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            rows = await session.scalars(
                select(db.Finding)
                .where(
                    db.Finding.investigation_id == run.id,
                )
                .order_by(db.Finding.id)
            )
            return [Finding.model_validate(row.body) for row in rows]

    async def report(self, public_id: str) -> Report:
        async with self.persistence.database.session() as session:
            run = await self.persistence.find(session, public_id)
            row = await session.scalar(
                select(db.Report).where(db.Report.investigation_id == run.id)
            )
            if row is None:
                raise HospitalError("REPORT_NOT_READY", 409)
            return Report.model_validate(row.body_json)
