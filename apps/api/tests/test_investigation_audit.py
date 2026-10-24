"""Public audit scope, pagination and parameter redaction."""

import pytest
from fastapi.testclient import TestClient
from test_investigation import setup_case

from app.composition import build_engine
from app.hospital.errors import HospitalError
from app.main import create_app
from app.schemas.investigation import CreateInvestigation


async def test_tool_audit_scope_allowlist_pagination_and_errors(tmp_path):
    settings, database, store = await setup_case(tmp_path)
    try:
        run, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), "audit")
        await store.transition(run, "running", "audit test")
        agent = await store.agent_start(run, "timeline")
        first = await store.tool_start(
            run,
            agent,
            "get_document",
            {
                "patient_id": "PAT-CONTROL",
                "document_id": "DOC-CONTROL",
                "api_key": "PRIVATE",
                "prompt": "PRIVATE",
                "status": {"secret": "PRIVATE"},
            },
            "timeline",
        )
        await store.tool_end(run, first, [{"type": "document", "id": "DOC-CONTROL"}])
        second = await store.tool_start(run, agent, "get_encounters", {}, "timeline")
        await store.tool_end(run, second, [], "TOOL_TIMEOUT")
        other, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), "other")
        assert (await store.queries.tools(other, 20, 0)).total == 0
        page = await store.queries.tools(run, 1, 0)
        assert page.total == 2 and len(page.items) == 1
        call = page.items[0]
        assert call.arguments == {"patient_id": "PAT-CONTROL", "document_id": "DOC-CONTROL"}
        assert call.agent_run_id == str(agent) and call.attempt == 1
        assert call.duration_ms is not None and call.duration_ms >= 0
        assert call.source_refs[0].id == "DOC-CONTROL"
        assert "PRIVATE" not in page.model_dump_json()
        assert (await store.queries.tools(run, 1, 1)).items[0].error_code == "TOOL_TIMEOUT"
        assert not (await store.queries.tools(run, 1, 2)).items
        with pytest.raises(HospitalError):
            await store.queries.tools("INV-MISSING", 20, 0)
    finally:
        await database.dispose()
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/investigations/{run}/tools?limit=1").json()["total"] == 2
        assert client.get("/api/investigations/INV-MISSING/tools").status_code == 404
        for query in ["limit=0", "limit=101", "offset=-1"]:
            assert client.get(f"/api/investigations/{run}/tools?{query}").status_code == 422


@pytest.mark.parametrize(
    "strategy,reasoning", [("baseline", "legacy"), ("adaptive_rules", "structured")]
)
async def test_case001_public_audit_matches_real_events(tmp_path, strategy, reasoning):
    settings, database, store = await setup_case(tmp_path, True)
    settings.investigation_strategy = strategy
    settings.investigation_reasoning = reasoning
    try:
        run, _ = await store.create(CreateInvestigation(patient_id="SYN-001"), "real-audit")
        await build_engine(store, settings).execute(run)
        events = await store.events(run, 0, 1000)
        completed = {
            e.payload["tool_execution_id"]: e for e in events if e.type == "tool.completed"
        }
        page = await store.queries.tools(run, 100, 0)
        assert page.total == len(completed)
        assert {call.id for call in page.items} == set(completed)
        for call in page.items:
            assert call.status == "succeeded"
            assert [ref.model_dump() for ref in call.source_refs] == completed[call.id].payload[
                "source_refs"
            ]
            assert call.arguments["patient_id"] == "SYN-001"
            assert call.duration_ms is not None
        if strategy == "adaptive_rules":
            assert any(call.attempt > 1 for call in page.items)
            tasks = {
                e.payload.get("id", e.payload.get("task_id"))
                for e in events
                if e.type == "task.scheduled"
            }
            assert tasks and any(e.type == "lead.approved" for e in events)
            assert all(
                e.payload.get("task_id") in tasks for e in events if e.type == "task.assigned"
            )
    finally:
        await database.dispose()
    with TestClient(create_app(settings)) as client:
        first = client.get(f"/api/investigations/{run}/tools?limit=20").json()
        second = client.get(f"/api/investigations/{run}/tools?limit=20&offset=20").json()
        assert first["total"] == page.total and len(first["items"]) == 20
        assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
