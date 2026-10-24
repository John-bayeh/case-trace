"""Substitution, dependency direction and shared transactional guarantees."""

import ast
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from test_hospital import FIXTURE
from test_investigation import setup_case

from app.agents.specialists import MedicationAgent
from app.clinical.ports import ClinicalReader, ClinicalSource, SourceResolver
from app.composition import build_engine
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.hospital.errors import HospitalError
from app.hospital.schemas import DocumentResponse, DocumentSearchHit, Medication
from app.main import create_app
from app.models import investigation as db
from app.orchestration.state import RunConflict
from app.schemas.investigation import CreateInvestigation, SourceRecord, SourceRef, ToolInput
from app.tools.clinical import ClinicalTools, dispatch
from app.tools.ports import ScopedToolExecutor

APP = Path(__file__).parents[1] / "app"


class FixtureHospital:
    """Only existing control DTOs; no repository, session, or raw case capability."""

    def __init__(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document = dict(raw["documents"][0])
        document.pop("storage_path")
        document["has_asset"] = True
        self.items = {}
        for kind, dto in [
            ("medication", Medication.model_validate(raw["medications"][0])),
            ("document", DocumentResponse.model_validate(document)),
        ]:
            data = dto.model_dump(mode="json")
            self.items[(kind, data["id"])] = SourceRecord(
                source=SourceRef(type=kind, id=data["id"]),
                source_version=1,
                source_hash=digest(data),
                data=data,
            )

    async def resolve(self, patient_id, source):
        item = self.items.get((source.type, source.id))
        if patient_id != "PAT-CONTROL" or item is None:
            raise HospitalError()
        return item.model_copy(deep=True)

    async def records(self, source_type, patient_id, filters):
        if patient_id != "PAT-CONTROL":
            raise HospitalError()
        items = [
            v.model_copy(deep=True) for (kind, _), v in self.items.items() if kind == source_type
        ]
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return items[offset : offset + limit], len(items)

    async def search_documents(self, patient_id, query, filters):
        record = await self.resolve(patient_id, SourceRef(type="document", id="DOC-CONTROL"))
        data = record.data
        if query.casefold() not in data["text_content"].casefold():
            return [], 0
        return [
            DocumentSearchHit(
                id=data["id"],
                title=data["title"],
                document_type=data["document_type"],
                event_at=data["event_at"],
                snippet=data["text_content"],
                relevance_score=1.0,
            )
        ], 1


async def test_fixture_source_runs_real_tools_specialist_and_verifier_without_sqlite():
    source: ClinicalSource = FixtureHospital()
    assert isinstance(source, ClinicalReader) and isinstance(source, SourceResolver)
    clinical = ClinicalTools(source)
    calls = []

    async def execute(agent, agent_id, name, raw):
        calls.append(name)
        return await dispatch(clinical, name, ToolInput.model_validate(raw))

    executor = ScopedToolExecutor("PAT-CONTROL", execute)
    assert not hasattr(executor, "store") and not hasattr(executor, "clinical")
    output, records = await MedicationAgent(executor, "medication", uuid4()).run()
    assert calls[:2] == ["get_medication_history", "get_document"]
    # Reconciliation now performs bounded authorized searches beyond provenance links.
    assert 2 < len(calls) <= 10
    assert set(calls[2:]) == {"search_documents"}
    assert len(records) == 2 and len(output.candidates) == 1
    result, _ = await EvidenceVerifier(source, "PAT-CONTROL").verify(output.candidates[0])
    assert result.status == "verified"
    wrong, _ = await EvidenceVerifier(source, "OTHER").verify(output.candidates[0])
    assert wrong.status == "rejected"
    hit = await dispatch(
        clinical, "search_documents", ToolInput(patient_id="PAT-CONTROL", query="Pipeline")
    )
    assert hit.total == 1 and "snippet" in hit.records[0].data


async def test_local_and_fixture_adapter_contract_and_application_injection(tmp_path):
    settings, database, _ = await setup_case(tmp_path)
    try:
        local: ClinicalSource = SimulatedHospitalAdapter(
            database, LocalAssetReader(settings.resolved_asset_path)
        )
        fixture: ClinicalSource = FixtureHospital()
        assert isinstance(local, ClinicalReader) and isinstance(local, SourceResolver)
        for source in [local, fixture]:
            rows, total = await source.records("medication", "PAT-CONTROL", {"limit": 1})
            assert total == len(rows) == 1
            resolved = await source.resolve("PAT-CONTROL", rows[0].source)
            assert resolved == rows[0]
            assert resolved.source_hash == digest(resolved.data)
            with pytest.raises(HospitalError):
                await source.resolve("OTHER", rows[0].source)
            with pytest.raises(HospitalError):
                await source.resolve("PAT-CONTROL", SourceRef(type="document", id="MISSING"))
        assert (await local.records("medication", "PAT-CONTROL", {}))[0] == (
            await fixture.records("medication", "PAT-CONTROL", {})
        )[0]
        application = create_app(settings, clinical=fixture)
        async with application.router.lifespan_context(application):
            engine = application.state.investigation_engine
            assert engine.clinical is fixture
        assert not engine.tasks
    finally:
        await database.dispose()


def test_canonical_digest_is_byte_compatible():
    value = {"z": None, "a": ["synthetic — سجل", 7.0, True], "time": "2026-01-01T09:00:00+03:00"}
    expected = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert digest(value) == expected
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


async def test_shared_writer_atomic_rollback_cas_and_duplicate_creation(tmp_path):
    _, database, store = await setup_case(tmp_path)
    try:
        request = CreateInvestigation(patient_id="PAT-CONTROL")
        results = await asyncio.gather(*(store.create(request, "same-key") for _ in range(3)))
        assert len({id_ for id_, _ in results}) == 1
        assert sum(created for _, created in results) == 1
        identifier = results[0][0]
        assert store.commands.persistence is store.activity.persistence is store.queries.persistence
        await store.transition(identifier, "running", "test")
        before = await store.snapshot(identifier)
        # Force the CAS to observe a stale version inside the transaction.
        with pytest.raises(RunConflict):
            async with store.persistence.mutation(identifier, "must.rollback", {}) as (
                session,
                run,
            ):
                run.context = {**run.context, "limitations": ["must roll back"]}
                await session.execute(
                    update(db.Investigation)
                    .where(db.Investigation.id == run.id)
                    .values(version=999)
                )
        assert await store.snapshot(identifier) == before
        # A dependent-row failure must roll back the event, context and version together.
        with pytest.raises(RuntimeError):
            async with store.persistence.mutation(identifier, "must.rollback", {}) as (
                session,
                run,
            ):
                session.add(
                    db.AgentExecution(
                        investigation_id=run.id, agent_key="control", status="running"
                    )
                )
                raise RuntimeError("injected write failure")
        assert await store.snapshot(identifier) == before
        assert not [e for e in await store.events(identifier, 0) if e.type == "must.rollback"]
        async with database.session() as session:
            assert await session.scalar(select(db.AgentExecution)) is None
        with pytest.raises(HospitalError) as error:
            await store.report(identifier)
        assert error.value.code == "REPORT_NOT_READY"
        await store.transition(identifier, "failed", "test")
        with pytest.raises(RunConflict):
            await store.record(identifier, "late.event", {})
    finally:
        await database.dispose()


async def test_asset_io_occurs_after_read_session_released(tmp_path):
    settings, database, _ = await setup_case(tmp_path)
    try:
        calls = []

        class CheckingAssets:
            async def verified_path(self, descriptor):
                assert database.engine.pool.checkedout() == 0
                calls.append(descriptor.external_id)
                return await LocalAssetReader(settings.resolved_asset_path).verified_path(
                    descriptor
                )

        source = SimulatedHospitalAdapter(database, CheckingAssets())
        record = await source.resolve("PAT-CONTROL", SourceRef(type="document", id="DOC-CONTROL"))
        assert record.data["has_asset"] and len(calls) == 1
    finally:
        await database.dispose()


async def test_worker_shutdown_cancels_session_free_source_work(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    entered = asyncio.Event()

    class WaitingSource(FixtureHospital):
        async def resolve(self, patient_id, source):
            assert database.engine.pool.checkedout() == 0
            entered.set()
            await asyncio.Event().wait()

    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        engine = build_engine(store, settings, clinical=WaitingSource())
        engine.schedule(identifier)
        await asyncio.wait_for(entered.wait(), timeout=5)
        await engine.close()
        assert not engine.tasks
        assert (await store.snapshot(identifier))["status"] == "failed"
        events = await store.events(identifier, 0)
        assert {"agent.failed", "tool.failed", "investigation.failed"} <= {e.type for e in events}
        assert database.engine.pool.checkedout() == 0
    finally:
        await database.dispose()


def test_runtime_dependency_direction():
    groups = {
        "agents": [
            "sqlalchemy",
            "app.models",
            "app.core.database",
            "app.hospital",
            "app.orchestration",
            "app.tools.registry",
            "pathlib",
            "os",
            "openai",
            "anthropic",
        ],
        "tools": [
            "sqlalchemy",
            "app.models",
            "app.core.database",
            "app.hospital.repository",
            "app.hospital.service",
            "app.orchestration.store",
        ],
        "evidence": [
            "app.agents",
            "app.hospital.repository",
            "app.tools.clinical",
            "sqlalchemy",
            "app.models",
        ],
    }
    for group, forbidden in groups.items():
        for path in (APP / group).rglob("*.py"):
            imports = []
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                elif isinstance(node, ast.Import):
                    imports.extend(a.name for a in node.names)
            for name in imports:
                assert not any(name == f or name.startswith(f + ".") for f in forbidden), (
                    path,
                    name,
                )
    for path in APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("evaluation", "app.evaluation"))
        if path.parent.name == "routes":
            assert "sqlalchemy import" not in text and "session.execute(" not in text
    engine = (APP / "orchestration" / "engine.py").read_text()
    assert "HospitalRepository" not in engine and "self.store.database" not in engine
