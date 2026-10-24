"""Adaptive policies, actual scoped retrieval, partial results and durable handoffs."""

import asyncio
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from test_hospital import FIXTURE, migrate
from test_investigation import setup_case

from app.agents.runtime import SpecialistTaskAgent, propose_leads
from app.agents.specialists import LaboratoryAgent
from app.composition import build_engine
from app.core.config import Settings
from app.core.database import Database
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import ingest
from app.hospital.validation import validate_case
from app.models import investigation as db
from app.orchestration.planner import approve, fingerprint, initial_plan, task
from app.orchestration.store import InvestigationStore
from app.orchestration.supervisor import InvestigationSupervisor
from app.schemas.investigation import AgentResult, CreateInvestigation, SourceRecord, SourceRef
from app.schemas.planning import (
    InvestigationContext,
    InvestigativeLead,
    RetrievalAction,
    SourceIdentity,
    TaskResult,
)
from app.tools.clinical import ClinicalTools
from app.tools.ports import ScopedToolExecutor
from app.tools.registry import ToolRegistry


def record(kind="observation", id_="LAB-X", **data):
    data = {"patient_id": "PAT-X", **data}
    return SourceRecord(
        source=SourceRef(type=kind, id=id_), source_version=1, source_hash=digest(data), data=data
    )


def policy_fixture():
    context = InvestigationContext(
        investigation_id="INV-X", patient_id="PAT-X", objective="full_record_investigation"
    )
    parent = task(context, "laboratory", "Observed changing results")
    parent.status = "completed"
    context.tasks.append(parent)
    source = record(source_document_id="DOC-X", encounter_id="ENC-X")
    lead = InvestigativeLead(
        id="LEAD-X",
        originating_task=parent.id,
        source_agent="laboratory",
        question="What does the linked report document?",
        missing_information="Original report",
        assigned_agent="laboratory",
        sources=[SourceIdentity.of(source)],
        actions=[RetrievalAction(tool="get_document", arguments={"record_id": "DOC-X"})],
        reason="A changing measurement references this report.",
    )
    return context, parent, source, lead


@pytest.mark.parametrize(
    "objective,types,expected",
    [
        (
            "full_record_investigation",
            ["document", "observation", "medication"],
            {"timeline", "laboratory", "medication", "referrals"},
        ),
        ("laboratory_investigation", ["document"], set()),
        ("laboratory_investigation", ["observation"], {"laboratory"}),
        ("medication_investigation", ["medication", "observation"], {"medication"}),
        ("timeline_investigation", ["document", "observation"], {"timeline"}),
        ("contradiction_investigation", ["document"], {"timeline", "referrals"}),
    ],
)
def test_planning_uses_objective_and_available_modalities(objective, types, expected):
    context, parent, _, _ = policy_fixture()
    context.objective = objective
    context.manifest = [SourceIdentity.of(record(kind, f"SRC-{i}")) for i, kind in enumerate(types)]
    plan = initial_plan(context, parent.id)
    assert {t.task_type for t in plan} == expected
    assert all(t.dependencies == [parent.id] and t.reason for t in plan)


@pytest.mark.parametrize(
    "change,expected",
    [
        ("unknown_parent", "INVALID_HANDOFF"),
        ("wrong_originator", "INVALID_HANDOFF"),
        ("unfinished_parent", "INVALID_HANDOFF"),
        ("unknown_agent", "UNKNOWN_SPECIALIST"),
        ("unauthorized_tool", "TOOL_NOT_PERMITTED"),
        ("wrong_patient", "PATIENT_SCOPE_VIOLATION"),
        ("stale_hash", "UNKNOWN_OR_STALE_SOURCE"),
        ("stale_version", "UNKNOWN_OR_STALE_SOURCE"),
        ("missing_source", "UNKNOWN_OR_STALE_SOURCE"),
        ("foreign_source", "PATIENT_SCOPE_VIOLATION"),
        ("unrelated_id", "UNRELATED_SOURCE_REQUEST"),
        ("invalid_filters", "INVALID_FILTERS"),
        ("arbitrary_search", "UNSUPPORTED_RETRIEVAL_PURPOSE"),
        ("unsupported_action", "UNSUPPORTED_FOLLOWUP_TOOL"),
        ("depth", "DEPTH_BUDGET_EXHAUSTED"),
        ("task_budget", "TASK_BUDGET_EXHAUSTED"),
    ],
)
def test_approval_rejects_invalid_and_unbounded_handoffs(change, expected):
    context, parent, source, lead = policy_fixture()
    settings = Settings()
    if change == "unknown_parent":
        lead.originating_task = "MISSING"
    if change == "wrong_originator":
        lead.source_agent = "timeline"
    if change == "unfinished_parent":
        parent.status = "running"
    if change == "unknown_agent":
        lead.assigned_agent = "unknown"
    if change == "unauthorized_tool":
        lead.actions[0].tool = "get_referrals"
    if change == "wrong_patient":
        lead.actions[0].arguments["patient_id"] = "OTHER"
    if change == "stale_hash":
        lead.sources[0].hash = "0" * 64
    if change == "stale_version":
        lead.sources[0].version = 99
    if change == "missing_source":
        lead.sources[0].id = "MISSING"
    if change == "foreign_source":
        source.data["patient_id"] = "OTHER"
    if change == "unrelated_id":
        lead.actions[0].arguments["record_id"] = "FOREIGN"
    if change == "invalid_filters":
        lead.actions[0].arguments["sql"] = "invalid"
    if change == "arbitrary_search":
        lead.actions = [RetrievalAction(tool="search_documents", arguments={"query": "arbitrary"})]
    if change == "unsupported_action":
        lead.actions = [RetrievalAction(tool="get_lab_results")]
    if change == "depth":
        settings.investigation_max_depth = 0
    if change == "task_budget":
        settings.investigation_max_tasks = 1
    item, reason = approve(
        lead, context, {(source.source.type, source.source.id): source}, settings, set()
    )
    assert item is None and reason == expected


def test_duplicate_leads_share_one_task_and_preserve_versions():
    context, parent, source, lead = policy_fixture()
    seen = set()
    records = {(source.source.type, source.source.id): source}
    item, reason = approve(lead, context, records, Settings(), seen)
    assert reason == "APPROVED" and item.parent_task == parent.id
    assert item.sources[0].hash == source.source_hash and item.depth == 1
    other = lead.model_copy(update={"id": "ANOTHER", "question": "Different wording"})
    assert fingerprint(other) == fingerprint(lead)
    assert approve(other, context, records, Settings(), seen) == (None, "DUPLICATE_LEAD")


def test_typed_contracts_reject_unstructured_commands():
    context, _, _, lead = policy_fixture()
    raw = task(context, "laboratory", "Review results").model_dump()
    with pytest.raises(ValidationError):
        type(task(context, "laboratory", "Review")).model_validate({**raw, "task_type": "run_sql"})
    with pytest.raises(ValidationError):
        InvestigativeLead.model_validate({**lead.model_dump(), "sources": []})


async def persisted_planning(database, identifier):
    async with database.session() as session:
        run = await session.scalar(
            select(db.Investigation).where(db.Investigation.external_id == identifier)
        )
        return run.context["planning"]


@pytest.mark.parametrize("reasoning", ["legacy", "structured"])
async def test_adaptive_canonical_runs_three_distinct_followups_and_verifies(tmp_path, reasoning):
    settings, database, store = await setup_case(tmp_path, True)
    settings.investigation_strategy = "adaptive_rules"
    settings.investigation_reasoning = reasoning
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="SYN-001"), None)
        engine = build_engine(store, settings)
        await asyncio.gather(engine.execute(identifier), engine.execute(identifier))
        report = await store.report(identifier)
        planning = await persisted_planning(database, identifier)
        assert {"timeline_contradiction", "laboratory_change", "medication_change"} <= {
            finding.type for finding in report.verified_findings
        }
        verifier = EvidenceVerifier(
            SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path)),
            "SYN-001",
            reasoning,
        )
        for finding in report.verified_findings:
            assert (await verifier.verify(finding))[0].status == "verified"
        assert report.execution_config["strategy"] == "adaptive_rules"
        actions = {
            a["tool"]
            for t in planning["tasks"]
            if t["task_type"] == "followup"
            for a in t["actions"]
        }
        assert {"get_document", "get_encounter", "search_documents"} <= actions
        assert all(t["status"] == "completed" for t in planning["tasks"])
        assert any(lead["status"] == "unresolved" for lead in planning["leads"])
        state = await store.snapshot(identifier)
        assert len({a["name"] for a in state["agents"]}) == len(state["agents"])
        events = await store.events(identifier, 0, 1000)
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        assigned = {e.payload["agent_run_id"] for e in events if e.type == "task.assigned"}
        assert assigned <= {e.payload["agent_run_id"] for e in events if e.type == "agent.started"}
        assert not [e for e in events if e.type == "tool.failed"]
        async with database.session() as session:
            calls = list(await session.scalars(select(db.ToolCall)))
            assert any(
                c.tool_name == "get_document" and c.sanitized_args.get("record_id") for c in calls
            )
            rows = list(await session.scalars(select(db.Report)))
            assert len(rows) == 1
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "limits",
    [
        {},
        {"investigation_max_depth": 0},
        {"investigation_max_tasks": 1},
        {"investigation_max_context_chars": 1000},
    ],
)
async def test_control_and_budgets_do_not_invent_contradictions(tmp_path, limits):
    settings, database, store = await setup_case(tmp_path)
    settings.investigation_strategy = "adaptive_rules"
    for key, value in limits.items():
        setattr(settings, key, value)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(identifier)
        state = await store.snapshot(identifier)
        if state["status"] == "failed":
            assert limits.get("investigation_max_context_chars") == 1000
            return
        report = await store.report(identifier)
        assert not [f for f in report.verified_findings if f.type == "timeline_contradiction"]
        planning = await persisted_planning(database, identifier)
        assert not planning["leads"]
        assert len(planning["tasks"]) <= settings.investigation_max_tasks
        if limits.get("investigation_max_tasks") == 1:
            assert report.status == "completed_with_limitations"
            assert planning["stop_reason"] == "budget_exhaustion"
    finally:
        await database.dispose()


@pytest.mark.parametrize("kind", ["laboratory", "medication", "timeline"])
async def test_independent_runtime_records_trigger_distinct_leads(tmp_path, kind):
    settings, database, store = await setup_case(tmp_path)
    try:
        clinical = SimulatedHospitalAdapter(
            database, LocalAssetReader(settings.resolved_asset_path)
        )
        observation = await clinical.resolve(
            "PAT-CONTROL", SourceRef(type="observation", id="LAB-CONTROL")
        )
        medication = await clinical.resolve(
            "PAT-CONTROL", SourceRef(type="medication", id="MED-CONTROL")
        )
        note = await clinical.resolve("PAT-CONTROL", SourceRef(type="document", id="DOC-CONTROL"))
        event = await clinical.resolve(
            "PAT-CONTROL", SourceRef(type="clinical_event", id="EVT-CONTROL")
        )
        context = InvestigationContext(
            investigation_id="INV-X",
            patient_id="PAT-CONTROL",
            objective="full_record_investigation",
        )
        parent = task(context, kind, "Independent synthetic control variation")
        parent.status = "completed"
        context.tasks.append(parent)
        records = []
        analysis = AgentResult()
        if kind == "laboratory":
            from app.agents.analysis import lab_changes

            later = observation.model_copy(deep=True)
            later.source.id = "LAB-INDEPENDENT"
            later.data.update(
                id=later.source.id,
                value_numeric=17,
                specimen_collected_at="2026-03-01T09:00:00Z",
                reported_at="2026-03-01T10:00:00Z",
            )
            later.source_hash = digest(later.data)
            records = [observation, later]
            analysis.candidates = lab_changes(records)
        elif kind == "medication":
            medication.data["status"] = "discontinued"
            medication.source_hash = digest(medication.data)
            records = [medication]
        else:
            from app.agents.analysis import contradictions

            note.data["text_content"] = "Cough first began on May 26, 2026; no cough before then."
            event.data["description"] = "Patient reports cough."
            note.source_hash, event.source_hash = digest(note.data), digest(event.data)
            records = [note, event]
            analysis.candidates = contradictions([note], [event])
        leads = propose_leads(
            parent,
            TaskResult(
                task_id=parent.id, agent=parent.assigned_agent, records=records, analysis=analysis
            ),
        )
        assert leads
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(identifier, "running", "test targeted handoff")
        registry = ToolRegistry(store, ClinicalTools(clinical), identifier, "PAT-CONTROL")
        supervisor = InvestigationSupervisor(
            store, ScopedToolExecutor("PAT-CONTROL", registry.execute), settings, context
        )
        supervisor.context.investigation_id = identifier
        supervisor.records = {(r.source.type, r.source.id): r for r in records}
        supervisor.context.leads = leads
        assert await supervisor.approve_leads(0)
        await supervisor.drain()
        executed = [t for t in context.tasks if t.task_type == "followup"]
        assert executed and all(t.status == "completed" for t in executed)
        assert registry.calls > 0
        events = await store.events(identifier, 0, 1000)
        assert any(e.type == "tool.completed" for e in events)
        if kind == "timeline":
            assert any("No clarifying" in limitation for limitation in context.limitations)
        else:
            assert all(t.result_refs for t in executed)
    finally:
        await database.dispose()


async def test_task_failure_retry_dependencies_concurrency_and_recovery(tmp_path, monkeypatch):
    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(identifier, "running", "test scheduler")
        context = InvestigationContext(
            investigation_id=identifier,
            patient_id="PAT-CONTROL",
            objective="full_record_investigation",
        )

        async def unused(*args):
            raise AssertionError("No tools needed in scheduler fixture")

        supervisor = InvestigationSupervisor(
            store, ScopedToolExecutor("PAT-CONTROL", unused), settings, context
        )
        active = 0
        maximum = 0
        attempts = {}
        overlap = asyncio.Event()

        async def execute(self, item):
            nonlocal active, maximum
            attempts[item.id] = attempts.get(item.id, 0) + 1
            if item.task_type == "laboratory" and attempts[item.id] == 1:
                raise TimeoutError()
            if item.task_type == "medication":
                raise ValueError("malformed specialist output")
            active += 1
            maximum = max(maximum, active)
            if active == settings.investigation_max_concurrency:
                overlap.set()
            await asyncio.wait_for(overlap.wait(), timeout=5)
            active -= 1
            return TaskResult(task_id=item.id, agent=item.assigned_agent)

        monkeypatch.setattr(SpecialistTaskAgent, "execute", execute)
        lab = task(context, "laboratory", "Retry transient read")
        lab.max_attempts = 2
        med = task(context, "medication", "Recoverable failure")
        independent = task(context, "timeline", "Independent")
        dependent = task(context, "referrals", "Must not execute", [med.id])
        for item in [lab, independent, med, dependent]:
            await supervisor.schedule(item)
        await supervisor.drain()
        assert lab.attempts == 2 and lab.status == "completed"
        assert med.status == "failed" and dependent.status == "skipped"
        assert dependent.id not in attempts and maximum == settings.investigation_max_concurrency

        async def invalid_identity(self, item):
            return TaskResult(task_id="FOREIGN-TASK", agent=self.name)

        monkeypatch.setattr(SpecialistTaskAgent, "execute", invalid_identity)
        invalid = task(context, "timeline", "Invalid result identity")
        await supervisor.schedule(invalid)
        await supervisor.drain()
        assert invalid.status == "failed" and invalid.error == "ValueError"
        cycle = task(context, "timeline", "Cycle")
        cycle.dependencies = [cycle.id]
        await supervisor.schedule(cycle)
        await supervisor.drain()
        assert cycle.status == "skipped" and cycle.error == "DEPENDENCY_CYCLE"
        pending = task(context, "laboratory", "Interrupted")
        await supervisor.schedule(pending)
        await supervisor.persist()
        await store.recover()
        recovered = await persisted_planning(database, identifier)
        assert next(t for t in recovered["tasks"] if t["id"] == pending.id)["status"] == "failed"
        assert (await store.snapshot(identifier))["status"] == "failed"
        # A crash can occur after scheduling commits but before the first checkpoint.
        interrupted, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(interrupted, "running", "before initial checkpoint")
        second_context = InvestigationContext(
            investigation_id=interrupted,
            patient_id="PAT-CONTROL",
            objective="full_record_investigation",
        )
        second = InvestigationSupervisor(
            store,
            ScopedToolExecutor("PAT-CONTROL", unused),
            settings,
            second_context,
        )
        pending = task(second_context, "laboratory", "Scheduled without checkpoint")
        await second.schedule(pending)
        await store.recover()
        recovered = await persisted_planning(database, interrupted)
        assert recovered["tasks"][0]["status"] == "failed"
    finally:
        await database.dispose()


async def test_specialist_rejects_mismatched_typed_task():
    async def forbidden(*args):
        raise AssertionError("Unauthorized task must not retrieve")

    context, _, _, _ = policy_fixture()
    specialist = SpecialistTaskAgent(
        LaboratoryAgent(ScopedToolExecutor("PAT-X", forbidden), "laboratory", uuid4()),
        frozenset({"laboratory"}),
    )
    with pytest.raises(ValueError, match="UNSUPPORTED_AGENT_TASK"):
        await specialist.execute(task(context, "medication", "Wrong specialist"))


async def setup_variant(tmp_path, scenario):
    """Only this test's copied synthetic control is changed, before validated ingestion."""
    settings = Settings(
        app_env="test",
        investigation_strategy="adaptive_rules",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'variant.db'}",
        asset_storage_path=tmp_path / "assets",
    )
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    narratives = {
        "paraphrased": "Patient first noticed a headache on September 18, 2026.",
        "approximate": "First noticed headache in late September 2026.",
        "recurrent": "Another episode of headache started on September 18, 2026.",
        "negated": "Headache first started on September 18, 2026.",
    }
    if scenario in narratives:
        raw["documents"][0]["text_content"] = "SYNTHETIC. " + narratives[scenario]
        raw["documents"][0]["event_at"] = "2026-09-25T09:00:00+03:00"
        raw["documents"][0]["authored_at"] = "2026-09-25T10:00:00+03:00"
        raw["clinical_events"][0]["description"] = (
            "Patient denies headache." if scenario == "negated" else "Headache observed at triage."
        )
    if scenario in {"timeline", "correction", "conflicting"}:
        raw["documents"][0]["text_content"] = (
            "SYNTHETIC. Cough first began on February 1, 2026; no cough before then."
            + (
                " Correction: episode attribution requires review."
                if scenario == "correction"
                else ""
            )
        )
        raw["documents"][0]["event_at"] = "2026-03-01T09:00:00+03:00"
        raw["documents"][0]["authored_at"] = "2026-03-01T10:00:00+03:00"
        raw["clinical_events"][0]["description"] = "Patient reports cough."
        if scenario == "conflicting":
            second = {
                **raw["documents"][0],
                "id": "DOC-CONFLICTING",
                "storage_path": None,
                "text_content": "SYNTHETIC. Cough first began on February 2, 2026; "
                "no cough before then.",
            }
            raw["documents"].append(second)
    if scenario == "laboratory":
        later = {
            **raw["observations"][0],
            "id": "LAB-VARIANT",
            "value_numeric": 17,
            "specimen_collected_at": "2026-03-01T09:00:00+03:00",
            "reported_at": "2026-03-01T10:00:00+03:00",
        }
        raw["observations"].append(later)
    if scenario == "medication":
        raw["medications"][0]["status"] = "discontinued"
    if scenario == "missing":
        raw["observations"][0]["source_document_id"] = None
    source = tmp_path / "variant.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    asset = settings.resolved_asset_path / "cases/CONTROL-001/control.txt"
    asset.parent.mkdir(parents=True)
    asset.write_text(raw["documents"][0]["text_content"], encoding="utf-8")
    migrate(settings)
    database = Database(settings)
    await database.initialize()
    async with database.session() as session:
        await ingest(
            session, validate_case(source, LocalAssetStorage(settings.resolved_asset_path))
        )
    return settings, database, InvestigationStore(database)


@pytest.mark.parametrize(
    "scenario", ["timeline", "correction", "conflicting", "laboratory", "medication", "missing"]
)
async def test_independent_ingested_variations_end_to_end(tmp_path, scenario):
    settings, database, store = await setup_variant(tmp_path, scenario)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        planning = await persisted_planning(database, identifier)
        followups = [item for item in planning["tasks"] if item["task_type"] == "followup"]
        assert all(item["status"] == "completed" for item in followups)
        if scenario == "missing":
            assert not followups
        else:
            assert followups
        if scenario == "correction":
            assert max(item["depth"] for item in followups) == 2
            assert any(item["result_refs"] for item in followups)
        if scenario in {"timeline", "correction", "conflicting"}:
            assert any(f.type == "timeline_contradiction" for f in report.verified_findings)
            assert all(h.verdict == "inconclusive" for h in report.hypotheses)
            if scenario == "conflicting":
                assert (
                    len([f for f in report.verified_findings if f.type == "timeline_contradiction"])
                    == 2
                )
                # Equivalent correction searches are consolidated across both conflicts.
                assert len(followups) == 1
        else:
            assert not any(f.type == "timeline_contradiction" for f in report.verified_findings)
        assert "EVALUATION_SENTINEL_NEVER_SERVE" not in report.model_dump_json()
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "scenario", ["paraphrased", "approximate", "recurrent", "negated", "control"]
)
async def test_structured_independent_ingested_narratives(tmp_path, scenario):
    settings, database, store = await setup_variant(tmp_path, scenario)
    settings.investigation_reasoning = "structured"
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        conflicts = [f for f in report.verified_findings if f.type == "timeline_contradiction"]
        assert len(conflicts) == int(scenario == "paraphrased")
        planning = await persisted_planning(database, identifier)
        followups = [t for t in planning["tasks"] if t["task_type"] == "followup"]
        assert bool(followups) == (scenario == "paraphrased")
        assert all(t["status"] == "completed" for t in followups)
        assert "EVALUATION_SENTINEL_NEVER_SERVE" not in report.model_dump_json()
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "setting,value,reason",
    [
        ("investigation_max_depth", 0, "DEPTH_BUDGET_EXHAUSTED"),
        ("investigation_max_followup_iterations", 0, "ITERATION_BUDGET_EXHAUSTED"),
        ("investigation_max_tasks", 5, "TASK_BUDGET_EXHAUSTED"),
        ("investigation_max_tool_calls", 12, "TOOL_BUDGET_EXHAUSTED"),
    ],
)
async def test_exhausted_real_leads_remain_unresolved(tmp_path, setting, value, reason):
    settings, database, store = await setup_variant(tmp_path, "timeline")
    setattr(settings, setting, value)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        planning = await persisted_planning(database, identifier)
        assert report.status == "completed_with_limitations"
        assert planning["stop_reason"] == "budget_exhaustion"
        assert any(lead["decision"] == reason for lead in planning["leads"])
        assert not any(t["task_type"] == "followup" for t in planning["tasks"])
    finally:
        await database.dispose()


async def test_duplicate_aliases_and_task_ids_are_not_executed_twice(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(identifier, "running", "test deduplication")
        context = InvestigationContext(
            investigation_id=identifier,
            patient_id="PAT-CONTROL",
            objective="full_record_investigation",
        )
        source = record(
            "observation", "LAB-CONTROL", patient_id="PAT-CONTROL", source_document_id="DOC-CONTROL"
        )
        parent = task(context, "laboratory", "Change in observations")
        parent.status = "completed"
        context.tasks.append(parent)
        lead = InvestigativeLead(
            id="LEAD-A",
            originating_task=parent.id,
            source_agent="laboratory",
            question="Inspect associated report",
            missing_information="Report context",
            assigned_agent="laboratory",
            sources=[SourceIdentity.of(source)],
            actions=[RetrievalAction(tool="get_document", arguments={"record_id": "DOC-CONTROL"})],
            reason="Observed change",
        )
        duplicate = lead.model_copy(deep=True)
        duplicate.id = "LEAD-B"
        duplicate.actions[0].arguments = {"patient_id": "PAT-CONTROL", "document_id": "DOC-CONTROL"}
        context.leads = [lead, duplicate]
        registry = ToolRegistry(
            store,
            ClinicalTools(
                SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
            ),
            identifier,
            "PAT-CONTROL",
        )
        supervisor = InvestigationSupervisor(
            store, ScopedToolExecutor("PAT-CONTROL", registry.execute), settings, context
        )
        supervisor.records = {("observation", "LAB-CONTROL"): source}
        assert await supervisor.approve_leads(0) == 1
        assert duplicate.status == "rejected" and duplicate.decision == "DUPLICATE_LEAD"
        item = context.tasks[-1]
        await supervisor.schedule(item)
        assert len(context.tasks) == 2
        await supervisor.drain()
        assert registry.calls == 1 and item.status == "completed"
    finally:
        await database.dispose()


async def test_missing_target_is_failed_and_audited_without_fabrication(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(identifier, "running", "test unavailable target")
        context = InvestigationContext(
            investigation_id=identifier,
            patient_id="PAT-CONTROL",
            objective="full_record_investigation",
        )
        parent = task(context, "laboratory", "Changing measurement")
        parent.status = "completed"
        context.tasks.append(parent)
        # A returned source can name an unavailable external report; it cannot invent it.
        source = record(source_document_id="DOC-UNAVAILABLE", patient_id="PAT-CONTROL")
        lead = InvestigativeLead(
            id="LEAD-MISSING",
            originating_task=parent.id,
            source_agent="laboratory",
            assigned_agent="laboratory",
            question="Retrieve original associated report",
            missing_information="Report unavailable",
            reason="Observed measurement change",
            sources=[SourceIdentity.of(source)],
            actions=[
                RetrievalAction(tool="get_document", arguments={"record_id": "DOC-UNAVAILABLE"})
            ],
        )
        context.leads.append(lead)
        registry = ToolRegistry(
            store,
            ClinicalTools(
                SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
            ),
            identifier,
            "PAT-CONTROL",
        )
        supervisor = InvestigationSupervisor(
            store, ScopedToolExecutor("PAT-CONTROL", registry.execute), settings, context
        )
        supervisor.records = {(source.source.type, source.source.id): source}
        assert await supervisor.approve_leads(0) == 1
        await supervisor.drain()
        assert context.tasks[-1].status == "failed" and not context.tasks[-1].result_refs
        assert not supervisor.result.candidates
        events = await store.events(identifier, 0, 1000)
        assert {"tool.failed", "task.failed", "agent.failed"} <= {e.type for e in events}
    finally:
        await database.dispose()
