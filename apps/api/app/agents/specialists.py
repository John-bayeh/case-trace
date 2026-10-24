"""Explicit specialists over the tool registry; no database, filesystem or provider SDK."""

from uuid import UUID

from app.agents import analysis
from app.clinical.diagnostic_challenger import diagnostic_comparisons
from app.clinical.longitudinal import (
    DOCUMENT_LIMIT,
    SEARCH_LIMIT,
    schedule,
)
from app.clinical.longitudinal import (
    candidate as series_candidate,
)
from app.clinical.medications import medication_relationships
from app.clinical.reasoning import reasoning_limitations
from app.clinical.result_followup import actionable, result_relationships, search_scope
from app.clinical.series import record_series
from app.hospital.errors import HospitalError
from app.schemas.investigation import AgentResult, Candidate, SourceRecord, ToolResult
from app.tools.ports import ToolExecutor


class Specialist:
    def __init__(
        self, tools: ToolExecutor, name: str, execution_id: UUID, reasoning: str = "legacy"
    ):
        self.tools, self.name, self.execution_id = tools, name, execution_id
        self.reasoning = reasoning

    async def call(self, tool: str, **args: object) -> ToolResult:
        return await self.tools.execute(
            self.name,
            self.execution_id,
            tool,
            {
                "patient_id": self.tools.patient_id,
                **args,
            },
        )

    async def collect(self, tool: str, **args: object) -> list[SourceRecord]:
        records = []
        offset = 0
        while True:
            page = await self.call(tool, limit=100, offset=offset, **args)
            records.extend(page.records)
            if not page.has_more:
                return records
            offset += len(page.records)
            if not page.records:
                raise ValueError("PAGINATION_STALLED")


class RetrievalAgent(Specialist):
    async def run(self) -> list[SourceRecord]:
        patient = await self.call("get_patient")
        manifest = patient.records
        for tool in [
            "get_encounters",
            "search_documents",
            "get_lab_results",
            "get_medication_history",
            "get_imaging_studies",
            "get_diagnostic_reports",
        ]:
            records = await self.collect(tool)
            # Manifest records are identifiers, not an indiscriminate agent context dump.
            manifest.extend(records)
        return manifest


class TimelineAgent(Specialist):
    async def run(self) -> tuple[AgentResult, list[SourceRecord]]:
        events = await self.collect("build_patient_timeline")
        encounters = await self.collect("get_encounters")
        notes = []
        for hit in await self.collect("search_clinical_notes"):
            notes.extend((await self.call("get_clinical_note", record_id=hit.source.id)).records)
        events.sort(key=lambda r: (str(r.data.get("occurred_at") or "~"), r.source.id))
        return AgentResult(
            candidates=analysis.contradictions(notes, events, self.reasoning),
            limitations=reasoning_limitations(notes + events)
            if self.reasoning == "structured"
            else [],
        ), events + encounters + notes


class LaboratoryAgent(Specialist):
    async def run(self) -> tuple[AgentResult, list[SourceRecord]]:
        records = await self.collect("get_lab_results")
        selected, limits = schedule(records)
        if not selected:
            return AgentResult(
                candidates=analysis.lab_changes(records)[:20], limitations=limits
            ), records
        sources = list(records)
        complete = True
        try:
            sources.extend(await self.collect("get_encounters"))
            sources.extend(await self.collect("get_referrals"))
            hits = await self.collect("search_documents")
            linked = {r.data.get("source_document_id") for _, values in selected for r in values}
            hits.sort(key=lambda r: (r.source.id not in linked, r.source.id))
            if len(hits) > DOCUMENT_LIMIT:
                complete = False
                limits.append(
                    f"Deferred laboratory documents: DOCUMENT_BUDGET_EXHAUSTED "
                    f"({len(hits) - DOCUMENT_LIMIT} originals not retrieved)."
                )
            for hit in hits[:DOCUMENT_LIMIT]:
                sources.extend(
                    (
                        await self.call(
                            "get_document",
                            record_id=hit.source.id,
                            source_version=hit.source_version,
                            source_hash=hit.source_hash,
                        )
                    ).records
                )
        except HospitalError as exc:
            if "BUDGET" not in exc.code and "TIMEOUT" not in exc.code:
                raise
            complete = False
            limits.append(
                f"Laboratory follow-up stopped: {exc.code}; retained measurements reassessed."
            )
        if len(sources) > SEARCH_LIMIT:
            return AgentResult(
                limitations=limits
                + [
                    "Deferred laboratory follow-up: SEARCH_MANIFEST_BUDGET_EXHAUSTED; "
                    "no absence conclusion proposed."
                ]
            ), sources
        reassessed = [series_candidate(key, values, sources, complete) for key, values in selected]
        for finding in reassessed:
            evidence = finding.longitudinal
            assert evidence is not None
            if (
                evidence.followup_state != "documented"
                or evidence.stop_reason == "budget_exhausted"
            ):
                limits.append(
                    f"Unresolved laboratory question [{evidence.group[:12]}]: "
                    f"{evidence.question} Stop: {evidence.stop_reason}."
                )
        covered = {r.source.id for _, values in selected for r in values}
        other = [
            c
            for c in analysis.lab_changes(records)
            if not {a.source.id for a in c.anchors} & covered
        ]
        if len(reassessed + other) > 20:
            limits.append("Laboratory candidate budget exhausted; additional changes deferred.")
        return AgentResult(candidates=(reassessed + other)[:20], limitations=limits), sources


class MedicationAgent(Specialist):
    async def run(self) -> tuple[AgentResult, list[SourceRecord]]:
        records = await self.collect("get_medication_history")
        if not records:
            return AgentResult(), []
        candidates = analysis.medication_observations(records)
        documents: dict[str, SourceRecord] = {}
        for record, candidate in zip(records, candidates, strict=True):
            document_id = record.data.get("source_document_id")
            if document_id:
                if document_id not in documents:
                    if len(documents) >= 20:
                        continue
                    documents[document_id] = (
                        await self.call("get_document", record_id=document_id)
                    ).records[0]
                item = analysis.anchor(documents[document_id], "text_content")
                item.relationship = "contextualizes"
                candidate.anchors.append(item)
        sources = records + list(documents.values())
        # Search by explicit ingredient and reconciliation actions, then retrieve originals.
        queries = list(
            dict.fromkeys(
                str(r.data.get("generic_name") or r.data.get("medication_name")) for r in records
            )
        )[:4] + ["medication", "dose", "hold", "restart"]
        for query in queries:
            if len(documents) >= 20:
                break
            for hit in await self.collect("search_documents", query=query):
                if hit.source.id in documents:
                    continue
                if len(documents) >= 20:
                    break
                original = await self.call(
                    "get_document",
                    record_id=hit.source.id,
                    source_version=hit.source_version,
                    source_hash=hit.source_hash,
                )
                if original.records:
                    documents[hit.source.id] = original.records[0]
        sources = records + list(documents.values())
        reconciled = medication_relationships(sources)
        series = record_series(sources)
        limits = []
        if len(documents) >= 20:
            limits.append("Medication document limit reached; history may be incomplete.")
        if len(reconciled) >= 6:
            limits.append(
                "Medication relationship limit reached; additional products may be unassessed."
            )
        if len(reconciled + candidates + series) > 20:
            limits.append(
                "Medication proposal limit reached; additional observations were not proposed."
            )
        if len(series) >= 12:
            limits.append(
                "Longitudinal observation limit reached; further groups may be unassessed."
            )
        return AgentResult(
            candidates=(reconciled + candidates + series)[:20],
            limitations=limits,
        ), sources


class ContradictionInvestigator(Specialist):
    async def followups(self) -> AgentResult:
        records = await self.collect("get_referrals")
        reports = await self.collect("get_diagnostic_reports")
        diagnostic_hits = await self.collect("search_documents", document_type="diagnostic_report")
        if (
            not any(actionable(r) or r.data.get("report_type") == "cardiology" for r in reports)
            and not diagnostic_hits
        ):
            return AgentResult(candidates=analysis.followups(records))
        # Unfiltered discovery prevents a disease-specific query from manufacturing
        # absence. Only twenty original documents fit the existing role budget.
        hits = await self.collect("search_documents")
        encounters = await self.collect("get_encounters")
        documents = []
        for hit in sorted(hits, key=lambda r: r.source.id)[:20]:
            original = await self.call(
                "get_document",
                record_id=hit.source.id,
                source_version=hit.source_version,
                source_hash=hit.source_hash,
            )
            documents.extend(original.records)
        sources = reports + records + encounters + documents
        complete = len(hits) == len(documents) and len(sources) <= 120
        if len(sources) > 120:
            return AgentResult(
                candidates=analysis.followups(records),
                limitations=[
                    "Result workflow search exceeded its manifest bound; no absence claim proposed."
                ],
            )
        scope = search_scope(sources, complete)
        return AgentResult(
            candidates=(
                diagnostic_comparisons(sources, scope)
                + result_relationships(sources, scope)
                + analysis.followups(records)
            )[:20],
            limitations=[]
            if complete
            else ["Result follow-up search was truncated; completion remains unknown."],
        )

    async def retrieve_candidates(self, candidates: list[Candidate]) -> None:
        # Targeted original-source retrieval and a deliberate correction search.
        seen = set()
        mapping = {
            "document": "get_document",
            "observation": "get_lab_result",
            "encounter": "get_encounter",
            "medication": None,
        }
        for candidate in candidates:
            for anchor in candidate.anchors:
                key = (anchor.source.type, anchor.source.id)
                tool = mapping.get(anchor.source.type)
                if tool and key not in seen:
                    await self.call(tool, record_id=anchor.source.id)
                    seen.add(key)
        await self.collect("search_documents", query="correction")
