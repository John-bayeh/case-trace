"""Real service/tool/worker integration; evaluation keys are read only after completion."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_hospital import FIXTURE, migrate

from app.agents.analysis import anchor, contradictions, timeline
from app.composition import build_engine
from app.core.config import Settings
from app.core.database import Database
from app.evidence.verification import EvidenceVerifier
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import ingest
from app.hospital.service import HospitalError
from app.hospital.validation import validate_case
from app.main import create_app
from app.models import investigation as db
from app.orchestration.store import InvestigationStore, RunConflict
from app.schemas.investigation import AgentResult, Candidate, CreateInvestigation, SourceRef
from app.tools.clinical import ClinicalTools
from app.tools.registry import ToolRegistry

ROOT = Path(__file__).resolve().parents[3]


async def setup_case(tmp_path: Path, canonical: bool = False):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'investigation.db'}",
        asset_storage_path=ROOT / "data/assets" if canonical else tmp_path / "assets",
    )
    migrate(settings)
    if canonical:
        source = ROOT / "data/cases/CASE-001/case.json"
    else:
        source = tmp_path / "control.json"
        source.write_bytes(FIXTURE.read_bytes())
        asset = settings.resolved_asset_path / "cases/CONTROL-001/control.txt"
        asset.parent.mkdir(parents=True)
        asset.write_text("SYNTHETIC — NOT FOR CLINICAL USE. Pipeline control.\n")
    database = Database(settings)
    await database.initialize()
    validated = validate_case(source, LocalAssetStorage(settings.resolved_asset_path))
    async with database.session() as session:
        await ingest(session, validated)
    return settings, database, InvestigationStore(database)


@pytest.mark.parametrize("reasoning", ["legacy", "structured"])
async def test_case001_engine_and_post_run_evaluation(tmp_path, reasoning):
    settings, database, store = await setup_case(tmp_path, True)
    settings.investigation_reasoning = reasoning
    try:
        id_, _ = await store.create(CreateInvestigation(patient_id="SYN-001"), "benchmark")
        engine = build_engine(store, settings)
        await engine.execute(id_)
        state = await store.snapshot(id_)
        assert state["status"] == "completed", state
        report = await store.report(id_)
        assert report.execution_mode == "deterministic_rules"
        conflicts = [f for f in report.verified_findings if f.type == "timeline_contradiction"]
        assert conflicts, report
        assert all(f.verification.status == "verified" for f in report.verified_findings)
        # Evaluator-only access happens strictly after the runtime finalized its persisted output.
        key = json.loads((ROOT / "evaluation/CASE-001/answer-key.json").read_text(encoding="utf-8"))
        assert key["dataset_version"] == "1.1"
        required = {s for f in key["expected_findings"] for s in f["required_source_ids"]}
        cited = {a.source.id for f in report.verified_findings for a in f.anchors}
        assert required <= cited
        assert "ground_truth" not in report.model_dump_json()
        assert state["progress"]["percent"] == 100
        events = await store.events(id_, 0, 1000)
        assert events[0].type == "investigation.started"
        started_tools = {e.payload["tool_execution_id"] for e in events if e.type == "tool.started"}
        ended_tools = {e.payload["tool_execution_id"] for e in events if e.type == "tool.completed"}
        assert started_tools == ended_tools
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        assert {
            "tool.started",
            "tool.completed",
            "finding.proposed",
            "finding.verified",
            "investigation.completed",
        } <= {e.type for e in events}
        verifier = EvidenceVerifier(
            ClinicalTools(
                SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
            ),
            "SYN-001",
            reasoning,
        )
        for finding in report.verified_findings:
            verification, _ = await verifier.verify(finding)
            assert verification.status == "verified"
        # Duplicate worker invocation cannot mutate a terminal run or duplicate its report.
        await engine.execute(id_)
        async with database.session() as session:
            assert await session.scalar(select(func.count()).select_from(db.Report)) == 1
        (tmp_path / "benchmark-report.json").write_text(report.model_dump_json(indent=2))
    finally:
        await database.dispose()


async def test_control_no_contradiction_and_recovery(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        request = CreateInvestigation(patient_id="PAT-CONTROL")
        id_, created = await store.create(request, "once")
        assert created
        assert await store.create(request, "once") == (id_, False)
        with pytest.raises(RunConflict):
            await store.transition(id_, "completed", "invalid")
        engine = build_engine(store, settings)
        await asyncio.gather(engine.execute(id_), engine.execute(id_))
        report = await store.report(id_)
        assert not [f for f in report.verified_findings if f.type == "timeline_contradiction"]
        pending, _ = await store.create(request, None)
        await store.transition(pending, "running", "test interrupted worker")
        await store.recover()
        assert (await store.snapshot(pending))["status"] == "failed"
        with pytest.raises(RunConflict):
            await store.transition(pending, "running", "cannot reopen")
    finally:
        await database.dispose()


async def test_verification_rejects_invented_values_hashes_and_patients(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        tools = ClinicalTools(
            SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
        )
        record = await tools.resolve("PAT-CONTROL", SourceRef(type="observation", id="LAB-CONTROL"))
        candidate = Candidate(
            type="clinical_relationship",
            title="Field",
            claim="Arbitrary claim must not be verified",
            claim_kind="observation",
            rule="field_observation",
            anchors=[anchor(record, "value_numeric")],
        )
        verifier = EvidenceVerifier(tools, "PAT-CONTROL")
        verified, rendered = await verifier.verify(candidate)
        assert verified.status == "verified" and rendered != candidate.claim
        mislabeled = candidate.model_copy(update={"type": "timeline_contradiction"})
        assert (await verifier.verify(mislabeled))[0].status == "inconclusive"
        for change in [
            {"expected": 999},
            {"source_hash": "0" * 64},
            {"source_version": 99},
            {"encounter_id": "OTHER"},
            {"field": "invented"},
        ]:
            invalid = candidate.model_copy(deep=True)
            invalid.anchors[0] = invalid.anchors[0].model_copy(update=change)
            assert (await verifier.verify(invalid))[0].status == "rejected"
        missing = candidate.model_copy(deep=True)
        missing.anchors[0].source.id = "INVENTED"
        assert (await verifier.verify(missing))[0].status == "rejected"
        assert (await EvidenceVerifier(tools, "OTHER").verify(candidate))[0].status == "rejected"
        # A correct reference does not automatically verify a clinical interpretation.
        candidate.rule, candidate.claim_kind = "interpretation", "hypothesis"
        assert (await verifier.verify(candidate))[0].status == "inconclusive"
    finally:
        await database.dispose()


async def test_permissions_budget_and_tool_failures_are_audited(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        id_, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(id_, "running", "test")
        agent = await store.agent_start(id_, "timeline")
        tools = ToolRegistry(
            store,
            ClinicalTools(
                SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
            ),
            id_,
            "PAT-CONTROL",
            max_calls=1,
        )
        for name, args in [("get_ground_truth", {}), ("get_encounters", {"patient_id": "OTHER"})]:
            with pytest.raises(HospitalError):
                await tools.execute("timeline", agent, name, {"patient_id": "PAT-CONTROL", **args})
        await tools.execute("timeline", agent, "get_encounters", {"patient_id": "PAT-CONTROL"})
        with pytest.raises(HospitalError):
            await tools.execute("timeline", agent, "get_encounters", {"patient_id": "PAT-CONTROL"})
        events = await store.events(id_, 0)
        assert sum(e.type == "tool.failed" for e in events) == 3
    finally:
        await database.dispose()


async def test_timeline_precision_and_parser_negative_controls(tmp_path):
    settings, database, _ = await setup_case(tmp_path)
    try:
        tools = ClinicalTools(
            SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
        )
        med = await tools.resolve("PAT-CONTROL", SourceRef(type="medication", id="MED-CONTROL"))
        event = timeline([med])[0]
        assert event.precision == "day" and event.timestamp == "2026-01-02"
        assert event.timestamps["ordered_at"] != event.timestamp
        note = await tools.resolve("PAT-CONTROL", SourceRef(type="document", id="DOC-CONTROL"))
        clinical = await tools.resolve(
            "PAT-CONTROL", SourceRef(type="clinical_event", id="EVT-CONTROL")
        )
        assert contradictions([note], [clinical]) == []
        note.data["text_content"] = "Cough first began on May 26, 2026; no cough before then."
        clinical.data["description"] = "No cough reported."
        assert contradictions([note], [clinical]) == []
        clinical.data["description"] = "Patient reports cough."
        assert contradictions([note], [clinical])
        clinical.data["documented_at"] = "2026-06-01T00:00:00Z"
        assert contradictions([note], [clinical]) == []  # Not contemporaneous evidence.
        clinical.data["occurred_at"] = "2026-05-26T00:30:00+03:00"
        clinical.data["documented_at"] = "2026-05-26T01:00:00+03:00"
        assert contradictions([note], [clinical]) == []  # Same local day, not preceding onset.
        earlier = clinical.model_copy(deep=True)
        earlier.data["occurred_at"] = "2026-01-02T00:15:00+03:00"
        later = clinical.model_copy(deep=True)
        later.source.id = "LATER"
        later.data["occurred_at"] = "2026-01-01T22:00:00Z"
        assert timeline([later, earlier])[0].source.id == earlier.source.id
    finally:
        await database.dispose()


async def test_mock_provider_failure_is_partial_not_fake_success(tmp_path):
    settings, database, store = await setup_case(tmp_path)

    class BrokenProvider:
        mode = "mock_test"

        async def propose(self, role, evidence):
            raise ValueError("malformed model response")

    try:
        id_, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings, BrokenProvider()).execute(id_)
        report = await store.report(id_)
        assert report.status == "completed_with_limitations"
        assert report.execution_mode == "mock_test"
        assert any("contradiction failed" in item for item in report.limitations)
    finally:
        await database.dispose()


def test_api_background_execution_and_stream_replay(tmp_path):
    settings, database, _ = asyncio.run(setup_case(tmp_path))
    asyncio.run(database.dispose())
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/investigations",
            json={"patient_id": "PAT-CONTROL"},
            headers={"Idempotency-Key": "api-once"},
        )
        assert response.status_code == 202, response.text
        id_ = response.json()["investigation_id"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = client.get(f"/api/investigations/{id_}").json()
            if state["status"] not in {"queued", "running"}:
                break
            time.sleep(0.05)
        assert state["status"] == "completed", state
        assert client.get(f"/api/investigations/{id_}/report").status_code == 200
        events = client.get(f"/api/investigations/{id_}/events?limit=1000").json()["items"]
        cursor = events[-2]["sequence"]
        stream = client.get(
            f"/api/investigations/{id_}/stream", headers={"Last-Event-ID": str(cursor)}
        )
        assert f"id: {cursor + 1}" in stream.text
        assert f"id: {cursor}\n" not in stream.text
        duplicate = client.post(
            "/api/investigations",
            json={"patient_id": "PAT-CONTROL"},
            headers={"Idempotency-Key": "api-once"},
        )
        assert duplicate.json()["investigation_id"] == id_
        assert client.get("/api/investigations/absent").status_code == 404
        assert client.post("/api/investigations", json={"patient_id": "OTHER"}).status_code == 404


def test_agent_boundary_imports():
    forbidden = ["sqlalchemy", "app.core.database", "ground_truth", "read_text", "open("]
    for path in (ROOT / "apps/api/app/agents").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path


async def test_provider_structured_validation_retry_and_missing_configuration(monkeypatch):
    from urllib.error import HTTPError

    from app.llm.provider import GeminiProvider, ProviderError

    with pytest.raises(ProviderError, match="CONFIGURATION_MISSING"):
        await GeminiProvider(Settings(llm_api_key="", llm_model="")).propose("test", {})

    class Response:
        def __init__(self, output):
            self.output = output

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": self.output}]}}]}
            ).encode()

    attempts = []

    def send(request, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise HTTPError("https://example.invalid", 429, "rate limited", {}, None)
        return Response(AgentResult().model_dump_json())

    monkeypatch.setattr("app.llm.provider.urlopen", send)
    provider = GeminiProvider(Settings(llm_model="configured-test-model", llm_api_key="test-only"))
    assert await provider.propose("test", {}) == AgentResult()
    assert len(attempts) == 2
    monkeypatch.setattr("app.llm.provider.urlopen", lambda *a, **k: Response('{"invented":true}'))
    with pytest.raises(ProviderError, match="INVALID_OUTPUT"):
        await provider.propose("test", {})


async def test_missing_asset_and_actual_foreign_patient_fail_closed(tmp_path):
    settings, database, _ = await setup_case(tmp_path)
    try:
        raw = FIXTURE.read_text(encoding="utf-8-sig").replace("CONTROL", "OTHER")
        source = tmp_path / "other.json"
        source.write_text(raw, encoding="utf-8")
        asset = settings.resolved_asset_path / "cases/OTHER-001/control.txt"
        asset.parent.mkdir(parents=True)
        asset.write_text("SYNTHETIC — NOT FOR CLINICAL USE. Other patient.\n")
        async with database.session() as session:
            await ingest(
                session, validate_case(source, LocalAssetStorage(settings.resolved_asset_path))
            )
        clinical = ClinicalTools(
            SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
        )
        with pytest.raises(HospitalError):
            await clinical.resolve("PAT-CONTROL", SourceRef(type="document", id="DOC-OTHER"))
        original_asset = settings.resolved_asset_path / "cases/CONTROL-001/control.txt"
        original_asset.write_text("Changed asset contents, checksum must fail")
        with pytest.raises(HospitalError):
            await clinical.resolve("PAT-CONTROL", SourceRef(type="document", id="DOC-CONTROL"))
    finally:
        await database.dispose()


async def test_timeout_has_explicit_failed_run_and_audit(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        settings.investigation_timeout_seconds = 0.01
        id_, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(id_)
        assert (await store.snapshot(id_))["status"] == "failed"
        with pytest.raises(HospitalError):
            await store.report(id_)
    finally:
        await database.dispose()
