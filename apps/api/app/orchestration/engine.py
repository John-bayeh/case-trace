"""Bounded deterministic supervisor; individual failures preserve useful evidence."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import uuid4

from app.agents import analysis
from app.agents.specialists import (
    ContradictionInvestigator,
    LaboratoryAgent,
    MedicationAgent,
    RetrievalAgent,
    TimelineAgent,
)
from app.clinical.diagnostic_challenger import LIMITATIONS as DIAGNOSTIC_LIMITATIONS
from app.clinical.diagnostic_challenger import comparison_hypothesis
from app.clinical.longitudinal import consolidate
from app.clinical.medications import laboratory_questions
from app.clinical.ports import ClinicalSource
from app.clinical.relationship_synthesis import (
    RELATIONSHIP_ALTERNATIVES,
    RELATIONSHIP_LIMITATIONS,
    synthesize_relationships,
)
from app.clinical.relationships import investigative_relationships, medication_associations
from app.clinical.result_followup import LIMITATIONS as RESULT_FOLLOWUP_LIMITATIONS
from app.core.config import Settings
from app.core.provenance import digest, now
from app.evidence.verification import EvidenceVerifier
from app.llm.provider import LLMProvider
from app.orchestration.ports import InvestigationRuntime
from app.orchestration.reporting import build_report
from app.orchestration.state import RunConflict
from app.orchestration.supervisor import InvestigationSupervisor
from app.schemas.investigation import AgentResult, Candidate, Finding, Report, SourceRecord
from app.schemas.planning import InvestigationContext
from app.tools.clinical import ClinicalTools
from app.tools.ports import ScopedToolExecutor
from app.tools.registry import ToolRegistry

logger = logging.getLogger("casetrace.investigation")


class InvestigationEngine:
    def __init__(
        self,
        store: InvestigationRuntime,
        settings: Settings,
        clinical: ClinicalSource,
        provider: LLMProvider | None = None,
    ):
        self.store, self.settings = store, settings
        self.clinical = clinical
        self.provider = provider
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.semaphore = asyncio.Semaphore(1)

    def schedule(self, public_id: str) -> None:
        if public_id not in self.tasks:
            task = asyncio.create_task(self.execute(public_id))
            self.tasks[public_id] = task
            task.add_done_callback(lambda _: self.tasks.pop(public_id, None))

    async def close(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def execute(self, public_id: str) -> None:
        async with self.semaphore:
            try:
                await self.store.transition(public_id, "running", "Worker claimed run")
            except RunConflict:
                return
            try:
                async with asyncio.timeout(self.settings.investigation_timeout_seconds):
                    await self._run(public_id)
            except BaseException as exc:
                logger.error(
                    "investigation.failed",
                    extra={"investigation_id": public_id, "error_type": type(exc).__name__},
                )
                await asyncio.shield(
                    self.store.transition(
                        public_id,
                        "failed",
                        type(exc).__name__,
                    )
                )
                if isinstance(exc, asyncio.CancelledError):
                    raise

    async def _run(self, public_id: str) -> None:
        state = await self.store.snapshot(public_id)
        await self.store.context(public_id, execution_strategy=self.settings.investigation_strategy)
        patient = state["patient_id"]
        clinical = ClinicalTools(self.clinical)
        registry = ToolRegistry(
            self.store,
            clinical,
            public_id,
            patient,
            max_calls=self.settings.investigation_max_tool_calls,
            max_per_agent=self.settings.investigation_max_calls_per_agent,
            max_chars=self.settings.investigation_max_context_chars,
        )
        executor = ScopedToolExecutor(patient, registry.execute)
        limits: list[str] = []
        records: dict[tuple[str, str], SourceRecord] = {}
        proposals: list[Candidate] = []
        medication_proposals: list[Candidate] = []
        laboratory_proposals: list[Candidate] = []
        hypotheses = []
        model_succeeded = False

        async def run_agent(name: str, factory: Callable[[Any], Awaitable[Any]]) -> Any:
            execution = await self.store.agent_start(public_id, name)
            try:
                output = await factory(execution)
            except Exception as exc:
                await self.store.agent_end(public_id, execution, type(exc).__name__)
                limits.append(
                    f"{name} failed: {type(exc).__name__}; related conclusions incomplete."
                )
                logger.warning(
                    "agent.failed",
                    extra={
                        "investigation_id": public_id,
                        "agent_run_id": str(execution),
                        "error_type": type(exc).__name__,
                    },
                )
                return None
            except asyncio.CancelledError:
                await self.store.agent_end(public_id, execution, "CANCELLED")
                raise
            await self.store.agent_end(public_id, execution)
            return output

        planning = None
        if self.settings.investigation_strategy == "adaptive_rules":
            supervisor = InvestigationSupervisor(
                self.store,
                executor,
                self.settings,
                InvestigationContext(
                    investigation_id=public_id, patient_id=patient, objective=state["objective"]
                ),
                remaining_calls=lambda: registry.max_calls - registry.calls,
            )
            adaptive, sources, planning = await supervisor.run()
            proposals.extend(adaptive.candidates)
            medication_proposals = [
                c
                for c in adaptive.candidates
                if planning.candidate_origins.get(digest(c.model_dump(mode="json")), {}).get(
                    "agent"
                )
                == "medication"
            ]
            laboratory_proposals = [
                c
                for c in adaptive.candidates
                if planning.candidate_origins.get(digest(c.model_dump(mode="json")), {}).get(
                    "agent"
                )
                == "laboratory"
            ]
            limits.extend(planning.limitations)
            for record in sources:
                records[(record.source.type, record.source.id)] = record
            if self.provider:
                provider = self.provider
                model = await run_agent(
                    "contradiction",
                    lambda _: provider.propose(
                        "contradiction",
                        {
                            "objective": state["objective"],
                            "candidates": [c.model_dump(mode="json") for c in proposals],
                            "sources": [
                                r.model_dump(mode="json")
                                for r in records.values()
                                if r.representation == "source"
                            ][:20],
                        },
                    ),
                )
                if model:
                    model_succeeded = True
                    proposals.extend(model.candidates)
                    hypotheses.extend(model.hypotheses)
                    limits.extend(model.limitations)
        else:
            await self.store.stage(public_id, "record_discovery")
            manifest = await run_agent(
                "retrieval", lambda id_: RetrievalAgent(executor, "retrieval", id_).run()
            )
            if manifest is None:
                raise RuntimeError("RECORD_DISCOVERY_FAILED")
            if len(manifest) <= 1:
                raise RuntimeError("NO_CLINICAL_EVIDENCE")
            for record in manifest:
                if record.source.type in {"imaging_study", "diagnostic_report"}:
                    records[(record.source.type, record.source.id)] = record
            await self.store.record(public_id, "records.retrieved", {"record_count": len(manifest)})
            await self.store.stage(public_id, "record_discovery", True)
            await self.store.stage(public_id, "timeline_reconstruction")
            timeline_output = await run_agent(
                "timeline",
                lambda id_: TimelineAgent(
                    executor, "timeline", id_, self.settings.investigation_reasoning
                ).run(),
            )
            if timeline_output:
                result, sources = timeline_output
                proposals.extend(result.candidates)
                for record in sources:
                    records[(record.source.type, record.source.id)] = record
            await self.store.stage(public_id, "timeline_reconstruction", True)
            await self.store.stage(public_id, "specialist_analysis")
            outputs = await asyncio.gather(
                run_agent(
                    "laboratory", lambda id_: LaboratoryAgent(executor, "laboratory", id_).run()
                ),
                run_agent(
                    "medication", lambda id_: MedicationAgent(executor, "medication", id_).run()
                ),
            )
            if outputs[0]:
                laboratory_proposals = list(outputs[0][0].candidates)
            if outputs[1]:
                medication_proposals = list(outputs[1][0].candidates)
            for output in outputs:
                if output:
                    result, sources = output
                    proposals.extend(result.candidates)
                    limits.extend(result.limitations)
                    for record in sources:
                        records[(record.source.type, record.source.id)] = record
            await self.store.stage(public_id, "specialist_analysis", True)
            await self.store.stage(public_id, "contradiction_verification")

            async def investigate(id_: Any) -> AgentResult:
                nonlocal model_succeeded
                specialist = ContradictionInvestigator(executor, "contradiction", id_)
                # Target clinical discrepancy candidates, not every medication observation.
                await specialist.retrieve_candidates(
                    [c for c in proposals if c.type == "timeline_contradiction"]
                )
                result = await specialist.followups()
                if self.provider:
                    model = await self.provider.propose(
                        "contradiction",
                        {
                            "objective": state["objective"],
                            "candidates": [c.model_dump(mode="json") for c in proposals],
                            "sources": [
                                r.model_dump(mode="json")
                                for r in records.values()
                                if r.representation == "source"
                            ][:20],
                        },
                    )
                    model_succeeded = True
                    result.candidates.extend(model.candidates)
                    result.hypotheses.extend(model.hypotheses)
                    result.limitations.extend(model.limitations)
                return result

            extra = await run_agent("contradiction", investigate)
            if extra:
                proposals.extend(extra.candidates)
                hypotheses.extend(extra.hypotheses)
                limits.extend(extra.limitations)
        if self.settings.investigation_reasoning == "structured":
            sources = list(records.values())
            proposals.extend(investigative_relationships(sources))
            proposals.extend(medication_associations(sources))
            relationships = [
                c
                for c in synthesize_relationships(sources, states_only=True)
                if c.relationship
                and c.relationship.relationship_type == "recorded_state_difference"
            ]
            await self.store.record(
                public_id,
                "assertions.extracted",
                {
                    "assertion_count": len(
                        {
                            a.id
                            for c in relationships
                            if c.relationship
                            for a in c.relationship.assertions
                        }
                    ),
                    "relationship_count": len(relationships),
                },
            )
            for relationship in relationships:
                assert relationship.relationship is not None
                await self.store.record(
                    public_id,
                    "relationship.assembled",
                    {
                        "relationship_type": relationship.relationship.relationship_type,
                        "assertion_ids": [a.id for a in relationship.relationship.assertions],
                        "source_refs": [
                            {**a.anchor.source.model_dump(), "version": a.anchor.source_version}
                            for a in relationship.relationship.assertions
                        ],
                    },
                )
            proposals.extend(relationships)
        cross_specialist = laboratory_questions(
            medication_proposals,
            [c for c in laboratory_proposals if c.type == "laboratory_change"],
        )
        if cross_specialist:
            await self.store.record(
                public_id,
                "specialist.evidence_requested",
                {
                    "requesting_agent": "medication",
                    "providing_agent": "laboratory",
                    "question_count": len(cross_specialist),
                    "source_refs": [
                        a.source.model_dump() for c in cross_specialist for a in c.anchors
                    ],
                    "evidence_state": "proposals_pending_independent_verification",
                },
            )
            proposals.extend(cross_specialist)
        hypotheses.extend(analysis.challenge(proposals))
        verifier = EvidenceVerifier(self.clinical, patient, self.settings.investigation_reasoning)
        # Never accept model verdicts as established clinical explanations.
        for hypothesis in hypotheses:
            # Provider-supplied comparison envelopes cannot bypass reconstruction.
            hypothesis.comparison = None
            hypothesis.verdict = "inconclusive"
            for anchor in hypothesis.supports + hypothesis.weakens:
                probe = Candidate(
                    type="clinical_relationship",
                    title="Hypothesis citation check",
                    claim="Hypothesis evidence",
                    claim_kind="hypothesis",
                    rule="interpretation",
                    anchors=[anchor],
                )
                result, _ = await verifier.verify(probe)
                if result.status == "rejected":
                    hypothesis.supports = []
                    hypothesis.weakens = []
                    hypothesis.missing_evidence.append("Proposed source anchors failed validation.")
                    limits.append(
                        "A model hypothesis contained invalid citations; its evidence was removed."
                    )
                    break
        proposals = consolidate(proposals)
        for deferred in proposals[self.settings.investigation_max_candidates :]:
            limits.append(f"Deferred candidate: {deferred.title}; CANDIDATE_BUDGET_EXHAUSTED.")
        for candidate in proposals[: self.settings.investigation_max_candidates]:
            finding_id = f"FND-{uuid4().hex}"
            if candidate.relationship:
                await self.store.record(
                    public_id,
                    "relationship.proposed",
                    {
                        "finding_id": finding_id,
                        "relationship_type": candidate.relationship.relationship_type,
                        "assertion_ids": [a.id for a in candidate.relationship.assertions],
                    },
                )
            await self.store.record(
                public_id,
                "finding.proposed",
                {
                    "finding_id": finding_id,
                    "source_refs": [a.source.model_dump() for a in candidate.anchors],
                    "rule": candidate.rule,
                    "candidate_type": candidate.type,
                    **(
                        planning.candidate_origins.get(
                            digest(candidate.model_dump(mode="json")), {}
                        )
                        if planning
                        else {}
                    ),
                },
            )
            await self.store.record(public_id, "verification.started", {"finding_id": finding_id})
            verification, canonical_claim = await verifier.verify(candidate)
            status: Literal["verified", "rejected", "unresolved"] = {
                "verified": "verified",
                "rejected": "rejected",
                "inconclusive": "unresolved",
            }[  # type: ignore[assignment]
                verification.status
            ]
            finding = Finding(
                **{
                    **candidate.model_dump(),
                    "claim": canonical_claim,
                    **(
                        {
                            "alternatives": RELATIONSHIP_ALTERNATIVES,
                            "limitations": RESULT_FOLLOWUP_LIMITATIONS
                            if candidate.relationship
                            and candidate.relationship.relationship_type == "result_followup"
                            else DIAGNOSTIC_LIMITATIONS
                            if candidate.relationship
                            and candidate.relationship.relationship_type == "hypothesis_challenge"
                            else RELATIONSHIP_LIMITATIONS,
                        }
                        if candidate.relationship and status == "verified"
                        else {}
                    ),
                    "title": {
                        "field_observation": "Verified source fields",
                        "lab_change": "Recorded laboratory change",
                        "onset_conflict": "Conflicting documented symptom chronology",
                        "clinical_relationship": "Recorded clinical relationship",
                    }.get(candidate.rule, candidate.title)
                    if status == "verified"
                    else candidate.title,
                },
                id=finding_id,
                investigation_id=public_id,
                status=status,
                verification=verification,
                support_level="strong"
                if status == "verified"
                else "insufficient"
                if status == "rejected"
                else "limited",
                created_at=now(),
                verified_at=now() if status == "verified" else None,
            )
            await self.store.save_finding(public_id, finding)
            if (
                status == "verified"
                and candidate.relationship
                and candidate.relationship.diagnostic_comparison
            ):
                hypotheses.append(
                    comparison_hypothesis(candidate.relationship.diagnostic_comparison)
                )
            if candidate.relationship:
                await self.store.record(
                    public_id,
                    "relationship.verification_completed",
                    {
                        "finding_id": finding_id,
                        "status": verification.status,
                        "relationship_type": candidate.relationship.relationship_type,
                        "assertion_count": len(candidate.relationship.assertions),
                    },
                )
            await self.store.record(
                public_id,
                "verification.completed",
                {
                    "finding_id": finding_id,
                    "status": verification.status,
                },
            )
        if len(proposals) > self.settings.investigation_max_candidates:
            limits.append("Finding budget exhausted; additional proposals were not assessed.")
        timeline = analysis.timeline(list(records.values()))
        await self.store.context(
            public_id,
            timeline=[e.model_dump(mode="json") for e in timeline],
            hypotheses=[h.model_dump(mode="json") for h in hypotheses],
            limitations=limits,
        )
        await self.store.stage(public_id, "contradiction_verification", True)
        await self.store.stage(public_id, "report_synthesis")

        async def synthesize(_: Any) -> Report:
            findings = await self.store.findings(public_id)
            return build_report(
                public_id,
                findings,
                timeline,
                hypotheses,
                limits,
                self.settings,
                self.provider if model_succeeded else None,
            )

        report = await run_agent("synthesis", synthesize)
        if report is None:
            raise RuntimeError("REPORT_SYNTHESIS_FAILED")
        if planning:
            report.execution_config.update(
                {
                    "strategy": "adaptive_rules",
                    "task_count": len(planning.tasks),
                    "lead_count": len(planning.leads),
                    "stop_reason": planning.stop_reason,
                    "duplicates_suppressed": planning.duplicates_suppressed,
                    "tool_calls": registry.calls,
                    "failed_tasks": sum(t.status == "failed" for t in planning.tasks),
                    "followup_depth": max((t.depth for t in planning.tasks), default=0),
                }
            )
        else:
            await self.store.context(public_id, execution_strategy="baseline")
        await self.store.stage(public_id, "report_synthesis", True)
        await self.store.finalize(public_id, report)
