"""Typed specialist execution and evidence-triggered proposals over scoped tools."""

from typing import Protocol
from uuid import uuid4

from app.agents import analysis
from app.agents.specialists import (
    ContradictionInvestigator,
    LaboratoryAgent,
    MedicationAgent,
    RetrievalAgent,
    Specialist,
    TimelineAgent,
)
from app.clinical.reasoning import reasoning_limitations
from app.core.provenance import digest
from app.schemas.investigation import AgentResult, SourceRecord
from app.schemas.planning import (
    InvestigationTask,
    InvestigativeLead,
    RetrievalAction,
    SourceIdentity,
    TaskResult,
)


class InvestigationAgent(Protocol):
    name: str
    supported_tasks: frozenset[str]

    async def execute(self, task: InvestigationTask) -> TaskResult: ...


def propose_leads(task: InvestigationTask, result: TaskResult) -> list[InvestigativeLead]:
    """Propose specific gaps from returned records, never from case identity."""
    leads: list[InvestigativeLead] = []

    def add(
        records: list[SourceRecord],
        actions: list[RetrievalAction],
        question: str,
        missing: str,
        agent: str,
        priority: int,
    ) -> None:
        leads.append(
            InvestigativeLead(
                id=f"LEAD-{uuid4().hex}",
                originating_task=task.id,
                source_agent=task.assigned_agent,
                question=question,
                missing_information=missing,
                assigned_agent=agent,
                sources=[SourceIdentity.of(r) for r in records],
                actions=actions,
                priority=priority,
                reason=question,
            )
        )

    by_key = {(r.source.type, r.source.id): r for r in result.records}
    if task.task_type == "timeline":
        for candidate in result.analysis.candidates:
            if candidate.type != "timeline_contradiction":
                continue
            relevant = list(
                {
                    (a.source.type, a.source.id): by_key[(a.source.type, a.source.id)]
                    for a in candidate.anchors
                    if (a.source.type, a.source.id) in by_key
                }.values()
            )
            if relevant:
                add(
                    relevant,
                    [RetrievalAction(tool="search_documents", arguments={"query": "correction"})],
                    "Does correcting documentation clarify the conflicting chronology?",
                    "A correction or episode clarification has not been retrieved.",
                    "contradiction",
                    100,
                )
    if task.task_type == "laboratory":
        for candidate in result.analysis.candidates:
            if candidate.longitudinal is not None:
                continue
            relevant = list(
                {
                    a.source.id: by_key[(a.source.type, a.source.id)]
                    for a in candidate.anchors
                    if (a.source.type, a.source.id) in by_key
                }.values()
            )
            for record in relevant:
                document = record.data.get("source_document_id")
                if document and ("document", document) not in by_key:
                    add(
                        [record],
                        [RetrievalAction(tool="get_document", arguments={"record_id": document})],
                        "What does the original report document about this changing measurement?",
                        "The observation's associated original report needs review.",
                        "laboratory",
                        70,
                    )
    if task.task_type == "medication":
        for record in result.records:
            if record.source.type != "medication" or record.data.get("status") not in {
                "discontinued",
                "completed",
                "held",
            }:
                continue
            encounter = record.data.get("encounter_id")
            if encounter:
                add(
                    [record],
                    [
                        RetrievalAction(tool="get_encounter", arguments={"record_id": encounter}),
                        RetrievalAction(
                            tool="search_documents", arguments={"encounter_id": encounter}
                        ),
                    ],
                    "What encounter documentation accompanies this medication status?",
                    "Order status alone does not explain the change or prove administration.",
                    "contradiction",
                    60,
                )
    if task.task_type == "followup" and any(
        action.tool == "search_documents" and action.arguments.get("query") == "correction"
        for action in task.actions
    ):
        for record in result.records:
            encounter = record.data.get("encounter_id")
            if record.source.type == "document" and encounter:
                add(
                    [record],
                    [RetrievalAction(tool="get_encounter", arguments={"record_id": encounter})],
                    "Which encounter is associated with the retrieved correcting documentation?",
                    "The correction's encounter context requires reassessment.",
                    "contradiction",
                    90,
                )
    grouped: dict[str, InvestigativeLead] = {}
    for lead in leads:
        key = digest([action.model_dump(mode="json") for action in lead.actions])
        previous = grouped.get(key)
        if previous:
            combined = {
                (s.type, s.id, s.version, s.hash): s for s in previous.sources + lead.sources
            }
            if len(combined) <= 20:
                previous.sources = list(combined.values())
                continue
            key = f"{key}:{lead.id}"
        grouped[key] = lead
    return list(grouped.values())


class SpecialistTaskAgent:
    """Compatibility adapter keeps established independently testable specialists."""

    def __init__(self, specialist: Specialist, supported_tasks: frozenset[str]):
        self.specialist = specialist
        self.name = specialist.name
        self.supported_tasks = supported_tasks

    async def execute(self, task: InvestigationTask) -> TaskResult:
        if task.assigned_agent != self.name or task.task_type not in self.supported_tasks:
            raise ValueError("UNSUPPORTED_AGENT_TASK")
        output = TaskResult(task_id=task.id, agent=self.name)
        if task.task_type == "followup":
            for action in task.actions:
                result = await self.specialist.call(action.tool, **action.arguments)
                output.records.extend(result.records)
                if result.has_more:
                    output.analysis.limitations.append(
                        "Targeted retrieval was truncated; more records exist."
                    )
            # Search hits are leads, never primary anchors. Retrieve originals before reassessment.
            originals = []
            for record in output.records:
                if record.representation == "search_hit":
                    originals.extend(
                        (
                            await self.specialist.call(
                                "get_document",
                                record_id=record.source.id,
                                source_version=record.source_version,
                                source_hash=record.source_hash,
                            )
                        ).records
                    )
                else:
                    originals.append(record)
            output.records = originals
            if not originals:
                output.analysis.limitations.append(
                    "No clarifying source was returned; the lead remains unresolved."
                )
            output.leads = propose_leads(task, output)
        elif task.task_type == "discovery":
            assert isinstance(self.specialist, RetrievalAgent)
            output.records = await self.specialist.run()
        elif task.task_type == "referrals":
            assert isinstance(self.specialist, ContradictionInvestigator)
            output.analysis = await self.specialist.followups()
        else:
            specialist = self.specialist
            assert isinstance(specialist, (TimelineAgent, LaboratoryAgent, MedicationAgent))
            output.analysis, output.records = await specialist.run()
            output.leads = propose_leads(task, output)
        return output


def reassess(records: list[SourceRecord], reasoning: str = "legacy") -> AgentResult:
    """Re-run established analyses on source records after targeted retrieval."""
    return AgentResult(
        candidates=analysis.contradictions(
            [r for r in records if r.source.type == "document"],
            [r for r in records if r.source.type == "clinical_event"],
            reasoning,
        ),
        limitations=reasoning_limitations(records) if reasoning == "structured" else [],
    )
