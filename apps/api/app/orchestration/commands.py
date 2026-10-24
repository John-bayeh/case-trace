"""Lifecycle mutations and atomic report publication."""

from typing import Any, cast
from uuid import uuid4

from sqlalchemy import select, update

from app.core.provenance import now
from app.hospital.repository import HospitalRepository
from app.hospital.service import ClinicalRecordService
from app.models import investigation as db
from app.orchestration.persistence import InvestigationPersistence
from app.orchestration.state import TRANSITIONS, RunConflict
from app.schemas.investigation import CreateInvestigation, Report


class InvestigationCommands:
    def __init__(self, persistence: InvestigationPersistence):
        self.persistence = persistence

    async def create(
        self,
        request: CreateInvestigation,
        key: str | None,
    ) -> tuple[str, bool]:
        async with (
            self.persistence.lock,
            self.persistence.database.session() as session,
            session.begin(),
        ):
            if key:
                existing = await session.scalar(
                    select(db.Investigation).where(
                        db.Investigation.idempotency_key == key,
                    )
                )
                if existing:
                    patient = await ClinicalRecordService(HospitalRepository(session)).patient(
                        request.patient_id,
                    )
                    if existing.patient_id != patient.id or existing.question != request.objective:
                        raise RunConflict()
                    return existing.external_id, False
            service = ClinicalRecordService(HospitalRepository(session))
            patient = await service.patient(request.patient_id)
            dataset = await service.repository.dataset(patient)
            public_id = f"INV-{uuid4().hex}"
            run = db.Investigation(
                external_id=public_id,
                patient_id=patient.id,
                dataset_id=patient.dataset_id,
                question=request.objective,
                idempotency_key=key,
                status="queued",
                created_at=now(),
                context={
                    "patient_id": request.patient_id,
                    "case_id": dataset.case_id,
                    "dataset_version": dataset.dataset_version,
                    "dataset_hash": dataset.seed_hash,
                    "limitations": [],
                    "timeline": [],
                    "hypotheses": [],
                    "current_stage": "queued",
                    "completed_stages": 0,
                },
            )
            session.add(run)
            await session.flush()
            return public_id, True

    async def transition(self, public_id: str, target: str, reason: str) -> None:
        payload: dict[str, Any] = {"to_state": target, "reason": reason}
        event = "investigation.started" if target == "running" else f"investigation.{target}"
        async with self.persistence.mutation(public_id, event, payload) as (session, run):
            if target not in TRANSITIONS.get(run.status, set()):
                raise RunConflict()
            payload["from_state"] = run.status
            if target in {"failed", "cancelled"}:
                planning = run.context.get("planning")
                if planning is None:
                    scheduled = await session.scalar(
                        select(db.InvestigationEvent)
                        .where(
                            db.InvestigationEvent.investigation_id == run.id,
                            db.InvestigationEvent.event_type == "task.scheduled",
                        )
                        .limit(1)
                    )
                    if scheduled:
                        planning = {
                            "investigation_id": public_id,
                            "patient_id": run.context["patient_id"],
                            "objective": run.question,
                            "tasks": [],
                            "leads": [],
                        }
                if planning:
                    # Durable task events can be newer than the last context checkpoint.
                    events = await session.scalars(
                        select(db.InvestigationEvent)
                        .where(
                            db.InvestigationEvent.investigation_id == run.id,
                            db.InvestigationEvent.event_type.in_(
                                [
                                    "task.scheduled",
                                    "task.completed",
                                    "task.failed",
                                    "task.cancelled",
                                    "task.skipped",
                                    "task.assigned",
                                ]
                            ),
                        )
                        .order_by(db.InvestigationEvent.sequence)
                    )
                    tasks = {t["id"]: t for t in planning.get("tasks", [])}
                    for event_row in events:
                        if event_row.event_type == "task.assigned":
                            item = tasks.get(event_row.payload["task_id"])
                            if item:
                                item["attempts"] = event_row.payload["attempt"]
                            continue
                        tasks[event_row.payload["id"]] = event_row.payload
                    for item in tasks.values():
                        if item["status"] in {"planned", "ready", "running"}:
                            item["status"] = "cancelled" if target == "cancelled" else "failed"
                            item["error"] = reason
                    for lead in planning.get("leads", []):
                        if lead["status"] in {"proposed", "approved"}:
                            lead["status"] = "unresolved"
                            lead["decision"] = reason
                    run.context = {
                        **run.context,
                        "planning": {
                            **planning,
                            "tasks": list(tasks.values()),
                            "stop_reason": reason,
                        },
                    }
                for model in [db.AgentExecution, db.ToolCall, db.InvestigationStage]:
                    await session.execute(
                        update(model)
                        .where(
                            cast(Any, model).investigation_id == run.id,
                            cast(Any, model).status == "running",
                        )
                        .values(
                            status="failed",
                            **(
                                {"completed_at": now(), "error_code": reason}
                                if model is db.ToolCall
                                else {"ended_at": now()}
                            ),
                        )
                    )
            run.status = target
            if target == "running":
                run.started_at = now()
            else:
                run.ended_at = now()

    async def context(self, public_id: str, **values: Any) -> None:
        async with self.persistence.mutation(public_id, "investigation.updated", {}) as (_, run):
            run.context = {**run.context, **values}

    async def finalize(self, public_id: str, report: Report) -> None:
        async with self.persistence.mutation(
            public_id,
            "investigation.completed",
            {
                "status": report.status,
            },
        ) as (session, run):
            if run.status != "running" or report.status not in {
                "completed",
                "completed_with_limitations",
            }:
                raise RunConflict()
            run.status, run.ended_at = report.status, now()
            session.add(
                db.Report(
                    investigation_id=run.id,
                    status="ready",
                    body_json=report.model_dump(mode="json"),
                    generated_at=now(),
                )
            )
