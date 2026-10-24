"""Bounded adaptive scheduler. Specialists retrieve; the existing verifier decides facts."""

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from app.agents.runtime import SpecialistTaskAgent, reassess
from app.agents.specialists import (
    ContradictionInvestigator,
    LaboratoryAgent,
    MedicationAgent,
    RetrievalAgent,
    TimelineAgent,
)
from app.clinical.longitudinal import consolidate
from app.core.config import Settings
from app.core.provenance import digest
from app.hospital.errors import HospitalError
from app.orchestration.planner import approve, initial_plan, task
from app.orchestration.ports import InvestigationRuntime
from app.schemas.investigation import AgentResult, SourceRecord, ToolResult
from app.schemas.planning import (
    InvestigationContext,
    InvestigationTask,
    SourceIdentity,
    TaskResult,
)
from app.tools.ports import ScopedToolExecutor, ToolExecutor

SPECIALISTS = {
    "retrieval": RetrievalAgent,
    "timeline": TimelineAgent,
    "laboratory": LaboratoryAgent,
    "medication": MedicationAgent,
    "contradiction": ContradictionInvestigator,
}
SUPPORTED = {
    "retrieval": frozenset({"discovery"}),
    "timeline": frozenset({"timeline"}),
    "laboratory": frozenset({"laboratory", "followup"}),
    "medication": frozenset({"medication", "followup"}),
    "contradiction": frozenset({"referrals", "followup"}),
}


class InvestigationSupervisor:
    def __init__(
        self,
        store: InvestigationRuntime,
        tools: ToolExecutor,
        settings: Settings,
        context: InvestigationContext,
        remaining_calls: Callable[[], int] | None = None,
    ):
        self.store, self.tools, self.settings, self.context = store, tools, settings, context
        self.records: dict[tuple[str, str], SourceRecord] = {}
        self.result = AgentResult()
        self.seen: set[str] = set()
        self.candidate_keys: set[str] = set()
        self.remaining_calls = remaining_calls

    async def event(self, name: str, payload: dict[str, object]) -> None:
        await self.store.record(self.context.investigation_id, name, payload)

    async def persist(self) -> None:
        # Task state and handoff history reuse the existing guarded context writer.
        await self.store.context(
            self.context.investigation_id,
            planning=self.context.model_dump(mode="json"),
            execution_strategy="adaptive_rules",
            limitations=self.context.limitations,
        )

    async def schedule(self, item: InvestigationTask) -> None:
        if any(existing.id == item.id for existing in self.context.tasks):
            await self.event("task.rejected", {"task_id": item.id, "reason": "DUPLICATE_TASK"})
            return
        if (
            item.patient_id != self.context.patient_id
            or item.investigation_id != self.context.investigation_id
            or item.task_type not in SUPPORTED.get(item.assigned_agent, frozenset())
        ):
            await self.event(
                "task.rejected", {"task_id": item.id, "reason": "INVALID_TASK_SCOPE_OR_TYPE"}
            )
            self.context.limitations.append(
                "A task with invalid scope or specialist assignment was rejected."
            )
            return
        if len(self.context.tasks) >= self.settings.investigation_max_tasks:
            item.status, item.error = "skipped", "TASK_BUDGET_EXHAUSTED"
            await self.event("task.skipped", item.model_dump(mode="json"))
            self.context.limitations.append(
                "Task budget exhausted; specialist work remains unfinished."
            )
            self.context.stop_reason = "budget_exhaustion"
            return
        if item.max_attempts == 1:
            item.max_attempts = self.settings.investigation_task_attempts
        item.max_tool_calls = min(
            item.max_tool_calls, self.settings.investigation_max_calls_per_agent
        )
        self.context.tasks.append(item)
        await self.event("task.scheduled", item.model_dump(mode="json"))

    async def execute_task(self, item: InvestigationTask) -> TaskResult | None:
        if item.status != "ready":
            raise ValueError("TASK_NOT_READY")
        item.status = "running"
        used_calls = 0

        async def execute_tool(
            agent: str, execution_id: UUID, name: str, arguments: dict[str, Any]
        ) -> ToolResult:
            nonlocal used_calls
            if used_calls >= item.max_tool_calls:
                raise HospitalError("TASK_TOOL_BUDGET_EXCEEDED", 409)
            used_calls += 1
            return await self.tools.execute(agent, execution_id, name, arguments)

        scoped = ScopedToolExecutor(item.patient_id, execute_tool)
        await self.event("task.started", {"task_id": item.id, "agent": item.assigned_agent})
        for attempt in range(item.max_attempts):
            item.attempts = attempt + 1
            execution = await self.store.agent_start(
                self.context.investigation_id, item.assigned_agent
            )
            await self.event(
                "task.assigned",
                {"task_id": item.id, "agent_run_id": str(execution), "attempt": item.attempts},
            )
            agent = SpecialistTaskAgent(
                SPECIALISTS[item.assigned_agent](
                    scoped, item.assigned_agent, execution, self.settings.investigation_reasoning
                ),
                SUPPORTED[item.assigned_agent],
            )
            try:
                output = TaskResult.model_validate(await agent.execute(item))
                if output.task_id != item.id or output.agent != item.assigned_agent:
                    raise ValueError("INVALID_TASK_RESULT_IDENTITY")
            except asyncio.CancelledError:
                item.status, item.error = "cancelled", "CANCELLED"
                await self.store.agent_end(self.context.investigation_id, execution, "CANCELLED")
                await self.event("task.cancelled", item.model_dump(mode="json"))
                raise
            except Exception as exc:
                item.error = getattr(exc, "code", type(exc).__name__)
                await self.store.agent_end(self.context.investigation_id, execution, item.error)
                await self.event(
                    "task.attempt_failed",
                    {"task_id": item.id, "error": item.error, "attempt": item.attempts},
                )
                # Retry only transient read failures; provider retries are separate.
                if item.error not in {"TimeoutError", "TOOL_TIMEOUT"}:
                    break
            else:
                output.execution_id = str(execution)
                item.status, item.error = "completed", None
                item.result_refs = [SourceIdentity.of(r) for r in output.records]
                await self.store.agent_end(self.context.investigation_id, execution)
                await self.event("task.completed", item.model_dump(mode="json"))
                return output
        item.status = "failed"
        self.context.limitations.append(
            f"{item.assigned_agent} task failed: {item.error}; work incomplete."
        )
        if item.error and "BUDGET" in item.error:
            self.context.stop_reason = "budget_exhaustion"
        await self.event("task.failed", item.model_dump(mode="json"))
        return None

    def merge(self, output: TaskResult) -> None:
        for record in output.records:
            key = (record.source.type, record.source.id)
            previous = self.records.get(key)
            if (
                previous
                and previous.representation == "source"
                and record.representation == "search_hit"
            ):
                continue
            proposed = {**self.records, key: record}
            if (
                sum(len(r.model_dump_json()) for r in proposed.values())
                > self.settings.investigation_max_context_chars
            ):
                self.context.limitations.append(
                    "Source context budget exhausted; some records were not retained."
                )
                self.context.stop_reason = "budget_exhaustion"
                break
            self.records[key] = record
        for candidate in consolidate(output.analysis.candidates):
            candidate_key = digest(candidate.model_dump(mode="json"))
            if candidate_key in self.candidate_keys:
                continue
            if len(self.result.candidates) >= self.settings.investigation_max_candidates:
                self.context.limitations.append(
                    f"Deferred candidate: {candidate.title}; CANDIDATE_BUDGET_EXHAUSTED."
                )
                self.context.stop_reason = "budget_exhaustion"
                continue
            self.candidate_keys.add(candidate_key)
            self.result.candidates.append(candidate)
            self.context.candidate_origins[candidate_key] = {
                "task_id": output.task_id,
                "agent": output.agent,
                "agent_run_id": output.execution_id or "deterministic_reassessment",
            }
        self.context.limitations.extend(output.analysis.limitations)
        room = self.settings.investigation_max_leads - len(self.context.leads)
        self.context.leads.extend(output.leads[:room])
        if len(output.leads) > room:
            self.context.limitations.append(
                "Lead budget exhausted; additional evidence gaps remain."
            )
            self.context.stop_reason = "budget_exhaustion"

    async def drain(self, kinds: set[str] | None = None) -> None:
        while True:
            states = {t.id: t.status for t in self.context.tasks}
            pending = [
                t
                for t in self.context.tasks
                if t.status == "planned" and (kinds is None or t.task_type in kinds)
            ]
            if not pending:
                return
            if self.remaining_calls and self.remaining_calls() <= 0:
                for item in pending:
                    item.status, item.error = "skipped", "TOOL_BUDGET_EXHAUSTED"
                    await self.event("task.skipped", item.model_dump(mode="json"))
                self.context.limitations.append(
                    "Tool budget exhausted; planned work remains incomplete."
                )
                self.context.stop_reason = "budget_exhaustion"
                await self.persist()
                return
            ready = []
            for item in pending:
                if any(
                    states.get(d) in {None, "failed", "cancelled", "skipped"}
                    for d in item.dependencies
                ):
                    item.status, item.error = "skipped", "DEPENDENCY_UNAVAILABLE"
                    self.context.limitations.append(
                        f"Task {item.task_type} skipped: dependency unavailable."
                    )
                    await self.event("task.skipped", item.model_dump(mode="json"))
                elif all(states[d] == "completed" for d in item.dependencies):
                    ready.append(item)
            if not ready:
                for item in pending:
                    if item.status == "planned":
                        item.status, item.error = "skipped", "DEPENDENCY_CYCLE"
                        self.context.limitations.append(
                            "Task dependency cycle prevented execution."
                        )
                        await self.event("task.skipped", item.model_dump(mode="json"))
                await self.persist()
                return
            ready.sort(key=lambda t: -t.priority)
            batch = ready[: self.settings.investigation_max_concurrency]
            for item in batch:
                item.status = "ready"
            await self.persist()
            # Each task owns its own audit calls/sessions. Batch size bounds concurrency.
            outputs = await asyncio.gather(*(self.execute_task(item) for item in batch))
            for output in outputs:
                if output:
                    self.merge(output)
            await self.persist()

    async def approve_leads(self, iteration: int) -> int:
        count = 0
        for lead in sorted(self.context.leads, key=lambda lead: -lead.priority):
            if lead.status != "proposed":
                continue
            await self.event("lead.identified", lead.model_dump(mode="json"))
            if self.remaining_calls and self.remaining_calls() < len(lead.actions):
                item, reason = None, "TOOL_BUDGET_EXHAUSTED"
            elif iteration >= self.settings.investigation_max_followup_iterations:
                item, reason = None, "ITERATION_BUDGET_EXHAUSTED"
            else:
                item, reason = approve(lead, self.context, self.records, self.settings, self.seen)
            lead.decision = reason
            lead.status = "approved" if item else "rejected"
            if reason == "DUPLICATE_LEAD":
                self.context.duplicates_suppressed += 1
            elif item is None:
                self.context.limitations.append(f"Unresolved lead: {lead.question} ({reason}).")
                if "BUDGET" in reason:
                    self.context.stop_reason = "budget_exhaustion"
            await self.event(
                "lead.approved" if item else "lead.rejected", lead.model_dump(mode="json")
            )
            if item:
                await self.schedule(item)
                count += 1
        return count

    async def run(self) -> tuple[AgentResult, list[SourceRecord], InvestigationContext]:
        discovery = task(
            self.context, "discovery", "Discover record categories before planning specialist work."
        )
        await self.schedule(discovery)
        await self.event("plan.created", {"strategy": "adaptive_rules", "task_id": discovery.id})
        await self.store.stage(self.context.investigation_id, "record_discovery")
        await self.drain()
        if discovery.status != "completed" or len(self.records) <= 1:
            raise RuntimeError("RECORD_DISCOVERY_FAILED")
        self.context.manifest = [SourceIdentity.of(r) for r in self.records.values()]
        present = {s.type for s in self.context.manifest}
        self.context.missing_modalities = sorted(
            {"document", "observation", "medication", "imaging_study"} - present
        )
        await self.store.stage(self.context.investigation_id, "record_discovery", True)
        for item in initial_plan(self.context, discovery.id):
            await self.schedule(item)
        await self.event(
            "plan.updated",
            {
                "missing_modalities": self.context.missing_modalities,
                "task_count": len(self.context.tasks),
            },
        )
        await self.store.stage(self.context.investigation_id, "timeline_reconstruction")
        await self.drain({"timeline"})
        timeline_tasks = [t for t in self.context.tasks if t.task_type == "timeline"]
        await self.store.stage(
            self.context.investigation_id,
            "timeline_reconstruction",
            True,
            "skipped"
            if not timeline_tasks
            else "completed"
            if all(t.status == "completed" for t in timeline_tasks)
            else "failed",
        )
        await self.store.stage(self.context.investigation_id, "specialist_analysis")
        await self.drain()
        for iteration in range(self.settings.investigation_max_followup_iterations + 1):
            if not await self.approve_leads(iteration):
                break
            await self.drain()
        for lead in self.context.leads:
            linked = next((t for t in self.context.tasks if t.lead_id == lead.id), None)
            if linked:
                lead.status = (
                    "completed"
                    if linked.status == "completed" and linked.result_refs
                    else "unresolved"
                )
        self.merge(
            TaskResult(
                task_id=f"REASSESS-{uuid4().hex}",
                agent="timeline",
                analysis=reassess(
                    [r for r in self.records.values() if r.representation == "source"],
                    self.settings.investigation_reasoning,
                ),
            )
        )
        self.context.limitations = list(dict.fromkeys(self.context.limitations))
        if self.context.stop_reason != "budget_exhaustion":
            if any(t.status in {"failed", "skipped"} for t in self.context.tasks):
                self.context.stop_reason = "partial_failure"
            elif any(
                lead.status in {"unresolved", "rejected"} and lead.decision != "DUPLICATE_LEAD"
                for lead in self.context.leads
            ):
                self.context.stop_reason = "evidence_exhaustion"
            else:
                self.context.stop_reason = "objectives_completed"
        await self.event(
            "plan.stopped",
            {"reason": self.context.stop_reason, "task_count": len(self.context.tasks)},
        )
        await self.persist()
        await self.store.stage(
            self.context.investigation_id,
            "specialist_analysis",
            True,
            "failed"
            if self.context.stop_reason in {"partial_failure", "budget_exhaustion"}
            else "completed",
        )
        await self.store.stage(self.context.investigation_id, "contradiction_verification")
        return (
            self.result,
            [r for r in self.records.values() if r.representation == "source"],
            self.context,
        )
