"""Direct contracts for all 20 tools, local/DTO-only adapters and cross-record retrieval."""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError
from test_investigation import setup_case

from app.core.provenance import digest
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.hospital.errors import HospitalError
from app.hospital.schemas import DocumentSearchHit
from app.schemas.investigation import SourceRef
from app.tools.clinical import TOOL_SPECS, ClinicalTools
from app.tools.inputs import INPUT_MODELS
from app.tools.registry import PERMISSIONS, ToolRegistry

PATIENT = "SYN-001"
PRIMARY = {
    "encounter": "started_at",
    "clinical_event": "occurred_at",
    "observation": "specimen_collected_at",
    "medication": "start_at",
    "document": "event_at",
    "imaging_study": "performed_at",
    "referral": "ordered_at",
    "diagnostic_report": "issued_at",
    "diagnosis": "diagnosed_at",
    "symptom": "onset_at",
}


class SnapshotSource:
    """Independent DTO-backed adapter, deliberately without database/file capabilities."""

    def __init__(self, items):
        self.items = {(r.source.type, r.source.id): r for r in items}

    async def resolve(self, patient_id, source):
        if patient_id != PATIENT or (source.type, source.id) not in self.items:
            raise HospitalError()
        return self.items[(source.type, source.id)].model_copy(deep=True)

    async def records(self, source_type, patient_id, filters):
        await self.resolve(patient_id, SourceRef(type="patient", id=patient_id))
        items = [
            r.model_copy(deep=True) for (kind, _), r in self.items.items() if kind == source_type
        ]
        time_field = filters.get("_time_field", PRIMARY[source_type])
        for key, value in filters.items():
            if key in {
                "limit",
                "offset",
                "sort",
                "_sort",
                "_casefold",
                "_time_field",
                "start_at",
                "end_at",
            }:
                continue
            items = [
                r
                for r in items
                if (
                    str(r.data.get(key)).casefold() == str(value).casefold()
                    if key in {"test_name", "medication_name", "body_region"}
                    else r.data.get(key) == value
                )
            ]

        def instant(r):
            raw = r.data.get(time_field)
            return datetime.fromisoformat(raw) if raw and len(raw) > 10 else None

        start, end = filters.get("start_at"), filters.get("end_at")
        items = [
            r
            for r in items
            if (not start or instant(r) and instant(r) >= start)
            and (not end or instant(r) and instant(r) <= end)
        ]
        items.sort(key=lambda r: r.source.id)
        known = [r for r in items if instant(r)]
        known.sort(key=instant, reverse=filters.get("_sort") == "desc")
        items = known + [r for r in items if not instant(r)]
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return items[offset : offset + limit], len(items)

    async def search_documents(self, patient_id, query, filters):
        await self.resolve(patient_id, SourceRef(type="patient", id=patient_id))
        hits = []
        for (kind, _), record in self.items.items():
            if kind != "document":
                continue
            d = record.data
            text = d.get("text_content") or ""
            position = text.casefold().find(query.casefold())
            if position < 0 and query.casefold() not in d["title"].casefold():
                continue
            if any(
                filters.get(key) and d.get(key) != filters[key]
                for key in ("document_type", "encounter_id")
            ):
                continue
            if (
                filters.get("department")
                and d["metadata"].get("department") != filters["department"]
            ):
                continue
            time = datetime.fromisoformat(d["event_at"]) if d["event_at"] else None
            if filters.get("start_at") and (time is None or time < filters["start_at"]):
                continue
            if filters.get("end_at") and (time is None or time > filters["end_at"]):
                continue
            begin = max(0, position - 40)
            hits.append(
                DocumentSearchHit(
                    **{k: d[k] for k in ("id", "title", "document_type", "event_at")},
                    snippet=text[begin : begin + 240],
                    relevance_score=1,
                )
            )
        hits.sort(key=lambda h: h.id)
        offset, limit = filters.get("offset", 0), filters.get("limit", 20)
        return hits[offset : offset + limit], len(hits)


class Audit:
    def __init__(self):
        self.started, self.ended = [], []
        self.events = []

    async def record(self, public_id, event, payload):
        self.events.append((event, payload))

    async def tool_start(self, public_id, agent_id, name, args, agent):
        self.started.append((name, args, agent))
        return uuid4()

    async def tool_end(self, public_id, call_id, refs, error=None):
        self.ended.append((refs, error))


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def sources(tmp_path_factory):
    settings, database, _ = await setup_case(tmp_path_factory.mktemp("tool-contracts"), True)
    local = SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
    items = [await local.resolve(PATIENT, SourceRef(type="patient", id=PATIENT))]
    for kind in PRIMARY:
        rows, _ = await local.records(kind, PATIENT, {"limit": 100})
        items.extend(rows)
    # Registered CASE-001 imaging metadata, not pixels or filesystem paths.
    items.append(
        await local.resolve(PATIENT, SourceRef(type="imaging_asset", id="IMG-ASSET-001-01"))
    )
    try:
        yield local, SnapshotSource(items)
    finally:
        await database.dispose()


def registry(source, **limits):
    audit = Audit()
    return ToolRegistry(audit, ClinicalTools(source), "INV-TOOLS", PATIENT, **limits), audit


def arguments(name):
    kind, operation = TOOL_SPECS[name]
    args = {}
    if operation == "get" and kind != "patient":
        args[
            {
                "encounter": "encounter_id",
                "document": "document_id",
                "observation": "observation_id",
                "medication": "medication_id",
                "diagnostic_report": "report_id",
                "imaging_asset": "imaging_asset_id",
            }[kind]
        ] = {
            "encounter": "ENC-001-01",
            "document": "DOC-001-01",
            "observation": "LAB-001-01",
            "medication": "MED-001-01",
            "diagnostic_report": "RPT-001-L1",
            "imaging_asset": "IMG-ASSET-001-01",
        }[kind]
    elif operation == "imaging_report":
        args["imaging_study_id"] = "IMG-001-01"
    elif operation == "compare":
        args = {"record_id": "LAB-001-01", "other_id": "LAB-001-06"}
    return args


def role(name):
    return next(agent for agent, names in PERMISSIONS.items() if name in names)


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("backend", [0, 1], ids=["sqlite", "dto"])
@pytest.mark.parametrize("name", sorted(TOOL_SPECS))
async def test_every_tool_direct_contract(sources, backend, name):
    source = sources[backend]
    tools, audit = registry(source)
    args = arguments(name)
    result = await tools.execute(role(name), uuid4(), name, args)
    assert result.records and result.retrieved_at.utcoffset() is not None
    assert result.source_refs == [r.source for r in result.records]
    for record in result.records:
        original = await source.resolve(PATIENT, record.source)
        assert record.source_version == original.source_version
        assert record.source_hash == digest(original.data)
        if record.representation == "source":
            assert record.data == original.data
        else:
            assert record.representation_hash == digest(record.data)
            assert (
                "text_content" not in record.data
                and record.data["snippet"] in original.data["text_content"]
            )
    assert audit.ended[-1][1] is None
    if name == "compare_lab_results":
        assert result.analysis is not None
    if args:
        missing = {key: "MISSING" for key in args}
        if name == "compare_lab_results":
            missing = {"record_id": "MISSING", "other_id": "LAB-001-06"}
        with pytest.raises(HospitalError):
            await tools.execute(role(name), uuid4(), name, missing)
    for bad in (
        {**args, "patient_id": "OTHER"},
        {**args, "unsupported": True},
        {**args, "patient_id": "../secret"},
    ):
        with pytest.raises((HospitalError, ValidationError)):
            await tools.execute(role(name), uuid4(), name, bad)
        assert audit.ended[-1][1] is not None
    # A missing selected patient must be an error for every tool, never an empty success.
    tools.patient_id = "MISSING"
    with pytest.raises(HospitalError):
        await tools.execute(role(name), uuid4(), name, args)
    assert len(audit.started) == len(audit.ended) == (6 if args else 5)


@pytest.mark.parametrize("name", sorted(INPUT_MODELS))
def test_each_input_model_rejects_unsupported_and_invalid_identifier(name):
    args = {"patient_id": PATIENT, **arguments(name)}
    for bad in ({**args, "secret": "hidden"}, {**args, "patient_id": "/etc/passwd"}):
        with pytest.raises(ValidationError):
            INPUT_MODELS[name].model_validate(bad)


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("backend", [0, 1])
async def test_targeted_filters_pagination_and_empty(sources, backend):
    tools, _ = registry(sources[backend])

    async def call(name, **raw):
        return await tools.execute(role(name), uuid4(), name, raw)

    for name in (
        "get_encounters",
        "get_lab_results",
        "get_medication_history",
        "get_diagnostic_reports",
        "get_imaging_studies",
        "get_referrals",
        "search_documents",
        "search_clinical_notes",
        "build_patient_timeline",
    ):
        all_ = await call(name, limit=100)
        paged = []
        for offset in range(all_.total):
            page = await call(name, limit=1, offset=offset)
            assert page.total == all_.total and page.has_more == (offset + 1 < all_.total)
            paged.extend(page.source_refs)
        assert paged == all_.source_refs and len(set(r.id for r in paged)) == len(paged)
        empty = await call(name, start_at="2099-01-01T00:00:00Z")
        assert empty.status == "empty" and empty.total == 0 and not empty.records
        for bad in (
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"offset": 10001},
            {"start_at": "2026-01-01T00:00:00"},
            {"start_at": "2027-01-01T00:00:00Z", "end_at": "2026-01-01T00:00:00Z"},
        ):
            with pytest.raises(ValidationError):
                await call(name, **bad)
        tools.calls = 0
        tools.agent_calls.clear()
    # Each supported selector and combinations are exercised against original source data.
    specs = {
        "get_encounters": ("encounter", ["department", "encounter_type", "status"]),
        "get_lab_results": ("observation", ["test_name", "test_code", "status", "encounter_id"]),
        "get_medication_history": ("medication", ["medication_name", "status", "encounter_id"]),
        "get_diagnostic_reports": ("diagnostic_report", ["report_type", "encounter_id"]),
        "get_imaging_studies": ("imaging_study", ["modality", "body_region", "encounter_id"]),
        "get_referrals": ("referral", ["status", "encounter_id"]),
    }
    for name, (_, fields) in specs.items():
        rows = (await call(name, limit=100)).records
        selected = rows[0].data
        filters = {f: selected[f] for f in fields}
        for f, value in filters.items():
            found = await call(name, **{f: value})
            assert found.records and all(r.data[f] == value for r in found.records)
        found = await call(name, **filters)
        assert rows[0].source in found.source_refs
        time_field = (
            "ordered_at" if name == "get_medication_history" else PRIMARY[rows[0].source.type]
        )
        exact = await call(name, start_at=selected[time_field], end_at=selected[time_field])
        assert rows[0].source in exact.source_refs
    referrals = await call("get_referrals", department="Pulmonology")
    assert all(r.data["referred_department"] == "Pulmonology" for r in referrals.records)


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("backend", [0, 1])
async def test_cross_record_scenarios(sources, backend):
    tools, _ = registry(sources[backend], max_per_agent=100)

    async def call(name, **raw):
        return await tools.execute(role(name), uuid4(), name, raw)

    # A: exact analyte retrieval, explicit pair and deterministic first/last selection.
    labs = await call("get_lab_results", test_code="HGB")
    assert len(labs.records) > 1
    compared = await call("compare_lab_results", test_name=labs.records[0].data["test_name"])
    assert compared.records == [labs.records[0], labs.records[-1]]
    assert compared.analysis.change_absolute == pytest.approx(
        labs.records[-1].data["value_numeric"] - labs.records[0].data["value_numeric"]
    )
    assert (await call("compare_lab_results", test_code="HGB")).analysis == compared.analysis
    # B: medication order chronology, exact source and source document.
    medications = await call(
        "get_medication_history", start_at="2026-01-01T00:00:00Z", end_at="2026-12-31T23:59:59Z"
    )
    for r in medications.records:
        exact = await call(
            "get_medication", medication_id=r.source.id, encounter_id=r.data["encounter_id"]
        )
        doc = await call("get_document", document_id=r.data["source_document_id"])
        assert exact.records[0] == r and doc.records[0].data["text_content"]
    # C: symptom search is substring retrieval, not a clinical conclusion.
    hits = await call("search_clinical_notes", query="COUGH")
    assert hits.records
    for hit in hits.records:
        note = (await call("get_clinical_note", document_id=hit.source.id)).records[0]
        assert "cough" in ((note.data["text_content"] or "") + note.data["title"]).casefold()
        filtered = await call(
            "search_documents",
            query="cough",
            document_type=note.data["document_type"],
            encounter_id=note.data["encounter_id"],
            start_at=note.data["event_at"],
            end_at=note.data["event_at"],
            department=note.data["metadata"].get("department"),
        )
        assert hit.source in filtered.source_refs
    # D: imaging, authored report, diagnostic association and illustrative metadata.
    studies = await call("get_imaging_studies", modality="X_RAY")
    study = studies.records[0]
    assert (await call("get_imaging_studies", imaging_study_id=study.source.id)).records == [study]
    report = await call("get_imaging_report", imaging_study_id=study.source.id)
    assert report.records[0].source.id == study.data["report_document_id"]
    diagnostics = await call("get_diagnostic_reports", imaging_study_id=study.source.id)
    assert diagnostics.records and all(
        r.data["document_id"] == report.records[0].source.id for r in diagnostics.records
    )
    asset = await call("get_imaging_asset_metadata", imaging_asset_id="IMG-ASSET-001-01")
    assert "storage_path" not in asset.records[0].data
    assert asset.records[0].data["metadata"].get("synthetic_label")
    # E: referrals are documented status/timing, with no inferred missed care.
    referrals = await call("get_referrals")
    assert referrals.records and all("ordered_at" in r.data for r in referrals.records)
    for r in referrals.records:
        assert (
            r.source
            in (
                await call(
                    "get_referrals",
                    department=r.data["referred_department"],
                    status=r.data["status"],
                )
            ).source_refs
        )
    timeline = await call(
        "build_patient_timeline",
        include=["events", "encounters", "medications", "documents"],
        limit=100,
    )
    assert len(timeline.timeline) == len(timeline.records)
    assert {r.source.type for r in timeline.records} == {
        "clinical_event",
        "encounter",
        "medication",
        "document",
    }
    for r, event in zip(timeline.records, timeline.timeline, strict=True):
        assert event.timestamp == r.data[event.timestamp_type]
        assert all(r.data[k] == v for k, v in event.timestamps.items())
    assert any(e.precision == "day" for e in timeline.timeline)


@pytest.mark.asyncio(loop_scope="module")
async def test_comparison_negative_and_stale_controls(sources):
    original = sources[1]
    for change, expected in [
        ({"test_code": "UNRELATED"}, "INCOMPARABLE_OBSERVATIONS"),
        ({"unit": "mg/L"}, "INCOMPARABLE_OBSERVATIONS"),
        ({"value_numeric": None, "value_text": "qualitative"}, "NON_NUMERIC_OBSERVATIONS"),
        ({"specimen_collected_at": None}, "UNKNOWN_COLLECTION_TIME"),
        ({"reported_at": "1900-01-01T00:00:00Z"}, None),
        ({"patient_id": "OTHER"}, "PATIENT_SCOPE_VIOLATION"),
    ]:
        items = [r.model_copy(deep=True) for r in original.items.values()]
        changed = next(r for r in items if r.source.id == "LAB-001-06")
        changed.data.update(change)
        changed.source_hash = digest(changed.data)
        tools, _ = registry(SnapshotSource(items))
        with pytest.raises((HospitalError, ValidationError)) as error:
            await tools.execute(
                "laboratory", uuid4(), "compare_lab_results", arguments("compare_lab_results")
            )
        if expected:
            assert error.value.code == expected
    tools, _ = registry(original)
    for raw in (
        {"record_id": "MISSING", "other_id": "LAB-001-06"},
        {"record_id": "LAB-001-01", "other_id": "LAB-001-01"},
        {"record_id": "LAB-001-01"},
        {"test_name": "absent"},
        {"record_id": "LAB-001-01", "other_id": "LAB-001-06", "test_code": "HGB"},
    ):
        with pytest.raises((HospitalError, ValidationError)):
            await tools.execute("laboratory", uuid4(), "compare_lab_results", raw)
    for raw in ({"source_version": 999}, {"source_hash": "0" * 64}):
        with pytest.raises(HospitalError) as error:
            await tools.execute(
                "timeline", uuid4(), "get_document", {"document_id": "DOC-001-01", **raw}
            )
        assert error.value.code == "STALE_SOURCE_REFERENCE"
    with pytest.raises(HospitalError) as error:
        await tools.execute(
            "timeline",
            uuid4(),
            "get_document",
            {"document_id": "DOC-001-01", "encounter_id": "ENC-001-07"},
        )
    assert error.value.code == "ENCOUNTER_SCOPE_VIOLATION"


@pytest.mark.asyncio(loop_scope="module")
async def test_registry_security_and_observability(sources):
    tools, audit = registry(sources[1], max_calls=1)
    assert len({entry["name"] for agent in PERMISSIONS for entry in tools.catalog(agent)}) == 20
    assert tools.catalog("synthesis") == []
    for agent, name in (
        ("synthesis", "get_patient"),
        ("medication", "get_lab_results"),
        ("timeline", "read_file"),
    ):
        with pytest.raises(HospitalError) as error:
            await tools.execute(agent, uuid4(), name, {"patient_id": PATIENT})
        assert error.value.code == "TOOL_NOT_PERMITTED"
    await tools.execute("retrieval", uuid4(), "get_patient", {})
    with pytest.raises(HospitalError) as error:
        await tools.execute("retrieval", uuid4(), "get_patient", {})
    assert error.value.code == "TOOL_BUDGET_EXCEEDED"
    assert len(audit.started) == len(audit.ended) == 5
    tools, audit = registry(sources[1], max_chars=20)
    with pytest.raises(HospitalError) as error:
        await tools.execute("retrieval", uuid4(), "get_patient", {})
    assert error.value.code == "TOOL_RESULT_TOO_LARGE" and audit.ended[-1][1]

    class SlowSource(SnapshotSource):
        async def resolve(self, patient_id, source):
            await asyncio.Event().wait()

    tools, audit = registry(SlowSource(list(sources[1].items.values())), timeout=0.001)
    with pytest.raises(TimeoutError):
        await tools.execute("retrieval", uuid4(), "get_patient", {})
    assert audit.ended[-1][1] == "TimeoutError"
    tools, audit = registry(sources[1])
    for category in ("referrals", "diagnoses", "symptoms", "imaging_studies", "diagnostic_reports"):
        with pytest.raises(HospitalError) as error:
            await tools.execute(
                "timeline", uuid4(), "build_patient_timeline", {"include": [category]}
            )
        assert error.value.code == "TOOL_NOT_PERMITTED"
    tools, audit = registry(sources[1], max_per_agent=1)
    await tools.execute("retrieval", uuid4(), "get_patient", {})
    with pytest.raises(HospitalError):
        await tools.execute("retrieval", uuid4(), "get_encounters", {})
    await tools.execute("timeline", uuid4(), "get_encounters", {})


@pytest.mark.asyncio(loop_scope="module")
async def test_patient_search_exact_associations_and_audit_redaction(sources):
    tools, audit = registry(sources[1])
    for query in ("syn-001", "mrn-syn-000001", "daniel"):
        result = await tools.execute("retrieval", uuid4(), "search_patient", {"query": query})
        assert result.source_refs == [SourceRef(type="patient", id=PATIENT)]
    result = await tools.execute("retrieval", uuid4(), "search_patient", {"query": "absent"})
    assert result.status == "empty"
    with pytest.raises(ValidationError):
        await tools.execute(
            "timeline",
            uuid4(),
            "get_document",
            {"record_id": "DOC-001-01", "document_id": "DOC-001-03"},
        )
    for name in (
        "get_lab_results",
        "get_medication_history",
        "get_diagnostic_reports",
        "get_imaging_studies",
        "search_documents",
        "build_patient_timeline",
    ):
        with pytest.raises(HospitalError):
            await tools.execute(role(name), uuid4(), name, {"encounter_id": "MISSING"})
    await tools.execute("timeline", uuid4(), "search_documents", {"query": "cough"})
    assert "cough" not in str(audit.started)
    assert "filter_fingerprint" in audit.started[-1][1]
    with pytest.raises(ValidationError):
        await tools.execute("timeline", uuid4(), "search_documents", {"query": "x" * 201})


@pytest.mark.asyncio(loop_scope="module")
async def test_numeric_edge_cases_and_reverse_pair(sources):
    items = [r.model_copy(deep=True) for r in sources[1].items.values()]
    first = next(r for r in items if r.source.id == "LAB-001-01")
    last = next(r for r in items if r.source.id == "LAB-001-06")
    first.data["value_numeric"] = 0
    first.source_hash = digest(first.data)
    tools, _ = registry(SnapshotSource(items))
    result = await tools.execute(
        "laboratory",
        uuid4(),
        "compare_lab_results",
        {"record_id": last.source.id, "other_id": first.source.id},
    )
    assert result.analysis.change_percent is None
    assert result.records[0].source == first.source
    assert result.analysis.change_absolute == last.data["value_numeric"]
    last.data["value_numeric"] = 0
    last.source_hash = digest(last.data)
    result = await tools.execute(
        "laboratory", uuid4(), "compare_lab_results", arguments("compare_lab_results")
    )
    assert result.analysis.direction == "unchanged"


@pytest.mark.asyncio(loop_scope="module")
async def test_output_provenance_rejects_duplicate_foreign_and_corrupt(sources):
    for mutation in ("duplicate", "hash", "id", "patient"):

        class BrokenSource(SnapshotSource):
            async def records(self, source_type, patient_id, filters, mutation=mutation):
                rows, total = await super().records(source_type, patient_id, filters)
                if mutation == "duplicate":
                    rows.append(rows[0].model_copy(deep=True))
                elif mutation == "hash":
                    rows[0].source_hash = "0" * 64
                elif mutation == "id":
                    rows[0].data["id"] = "WRONG"
                    rows[0].source_hash = digest(rows[0].data)
                else:
                    rows[0].data["patient_id"] = "OTHER"
                    rows[0].source_hash = digest(rows[0].data)
                return rows, total

        tools, audit = registry(BrokenSource(list(sources[1].items.values())))
        with pytest.raises(HospitalError):
            await tools.execute("laboratory", uuid4(), "get_lab_results", {})
        assert audit.ended[-1][1] is not None


async def test_persisted_actor_audit_and_ordered_events(tmp_path):
    from sqlalchemy import select

    from app.models.investigation import ToolCall
    from app.orchestration.state import RunConflict
    from app.schemas.investigation import CreateInvestigation

    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await store.transition(identifier, "running", "test")
        actor = await store.agent_start(identifier, "timeline")
        source = SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
        tools = ToolRegistry(store, ClinicalTools(source), identifier, "PAT-CONTROL")
        with pytest.raises(RunConflict):
            await tools.execute("medication", actor, "get_medication_history", {})
        with pytest.raises(RunConflict):
            await tools.execute("timeline", uuid4(), "get_document", {"record_id": "DOC-CONTROL"})
        await tools.execute("timeline", actor, "search_documents", {"query": "Pipeline"})
        with pytest.raises(HospitalError):
            await tools.execute("timeline", actor, "get_document", {"record_id": "MISSING"})
        async with database.session() as session:
            rows = list(await session.scalars(select(ToolCall).order_by(ToolCall.started_at)))
            assert [r.status for r in rows] == ["succeeded", "failed"]
            assert all(r.completed_at and r.duration_ms >= 0 for r in rows)
            assert rows[0].result_refs == [{"type": "document", "id": "DOC-CONTROL"}]
            assert "Pipeline" not in str(rows[0].sanitized_args)
            assert rows[1].error_code == "RESOURCE_NOT_FOUND"
        events = await store.events(identifier, 0)
        assert [e.sequence for e in events] == sorted({e.sequence for e in events})
        assert [e.type for e in events if e.type.startswith("tool.")] == [
            "tool.started",
            "tool.completed",
            "tool.page",
            "tool.started",
            "tool.failed",
        ]
        page = next(e for e in events if e.type == "tool.page")
        assert page.payload["record_count"] == 1
        assert page.payload["has_more"] is False
        assert page.payload["representations"] == ["search_hit"]
        assert "Pipeline" not in str(page.payload)
    finally:
        await database.dispose()
