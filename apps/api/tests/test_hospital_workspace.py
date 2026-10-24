"""Refactor 08 public read models and clinical browsing, isolated SQLite only."""

import json

import pytest
from fastapi.testclient import TestClient
from test_hospital import load
from test_hospital import setup as setup

from app.core.database import Database
from app.hospital.catalog import CaseCatalog
from app.hospital.repository import HospitalRepository
from app.hospital.service import ClinicalRecordService
from app.main import create_app
from app.orchestration.store import InvestigationStore
from app.schemas.investigation import CreateInvestigation


@pytest.fixture
def catalog_setup(setup, tmp_path):
    settings, source, storage = setup
    root = tmp_path / "catalog-root"
    (root / "apps/api").mkdir(parents=True)
    cases = root / "data/cases"
    (cases / "CONTROL-001").mkdir(parents=True)
    (cases / "CONTROL-001/case.json").write_bytes(source.read_bytes())
    (cases / "BROKEN").mkdir()
    (cases / "BROKEN/case.json").write_text('{"unexpected":"PRIVATE_ANSWER"}')
    settings = settings.model_copy(update={"casetrace_root": root})
    return settings, source, storage


async def test_catalog_readiness_counts_filters_and_ground_truth(catalog_setup):
    settings, source, storage = catalog_setup
    with TestClient(create_app(settings)) as client:
        before = client.get("/api/hospital/v1/cases").json()["data"]
        assert {r["case_id"]: r["status"] for r in before} == {
            "BROKEN": "invalid",
            "CONTROL-001": "available_not_imported",
        }
        assert client.get("/api/hospital/v1/cases/ABSENT").json()["data"]["status"] == "not_present"
        assert client.get("/api/hospital/v1/cases?case_id=../bad").status_code == 422
    await load(settings, source, storage)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/hospital/v1/cases?status=imported&limit=1")
        assert response.status_code == 200
        body = response.json()
        item = body["data"][0]
        raw = json.loads(source.read_text())
        assert item["case_id"] == "CONTROL-001"
        assert item["imported"] is True and item["dataset_status"] == "ready"
        assert item["display_name"] == raw["patient"]["display_name"]
        for category in ["encounters", "observations", "medications", "documents"]:
            assert item["counts"][category] == len(raw[category])
        assert item["modalities"] == ["OTHER", "text/plain"]
        assert client.get("/api/hospital/v1/cases?modality=application/pdf").json()["data"] == []
        assert (
            client.get("/api/hospital/v1/cases?limit=1&offset=1").json()["data"][0]["case_id"]
            == "CONTROL-001"
        )
        assert client.get("/api/hospital/v1/cases?limit=0").status_code == 422
        text = client.get("/api/hospital/v1/cases").text
        for forbidden in [
            "ground_truth",
            "PRIVATE_ANSWER",
            "source_hash",
            "storage_path",
            "validation",
            "expected_answer",
        ]:
            assert forbidden not in text
        assert client.get("/api/hospital/v1/cases/CONTROL-001").json()["data"] == item


async def test_catalog_missing_assets_conflict_and_production(catalog_setup):
    settings, source, storage = catalog_setup
    await load(settings, source, storage)
    asset = storage.root / "cases/CONTROL-001/control.txt"
    original = asset.read_bytes()
    asset.unlink()
    with TestClient(create_app(settings)) as client:
        assert (
            client.get("/api/hospital/v1/cases/CONTROL-001").json()["data"]["status"]
            == "missing_assets"
        )
    asset.write_bytes(original)
    case = settings.casetrace_root / "data/cases/CONTROL-001/case.json"
    raw = json.loads(case.read_text())
    raw["patient"]["display_name"] = "Changed synthetic source"
    case.write_text(json.dumps(raw))
    with TestClient(create_app(settings)) as client:
        assert (
            client.get("/api/hospital/v1/cases/CONTROL-001").json()["data"]["status"]
            == "source_conflict"
        )
    production = settings.model_copy(update={"app_env": "production"})
    with TestClient(create_app(production)) as client:
        data = client.get("/api/hospital/v1/cases").json()["data"]
        assert len(data) == 1 and data[0]["status"] == "imported"
        assert data[0]["display_name"] != "Changed synthetic source"
        assert client.get("/api/hospital/v1/cases/ABSENT").status_code == 404


async def test_history_pagination_filters_and_persisted_identity(catalog_setup):
    settings, source, storage = catalog_setup
    await load(settings, source, storage)
    database = Database(settings)
    try:
        store = InvestigationStore(database)
        first, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), "r08-first")
        second, _ = await store.create(
            CreateInvestigation(patient_id="PAT-CONTROL", objective="laboratory_investigation"),
            "r08-second",
        )
        # No worker is scheduled by this persistence setup.
        history = await store.queries.history("PAT-CONTROL", "CONTROL-001", "queued", 1, 0)
        assert history.total == 2 and history.items[0].id == second
        assert (await store.queries.history(None, None, None, 1, 1)).items[0].id == first
    finally:
        await database.dispose()
    with TestClient(create_app(settings)) as client:
        page = client.get("/api/investigations?patient_id=PAT-CONTROL&limit=1").json()
        assert page["total"] == 2 and len(page["items"]) == 1
        assert page["items"][0]["case_id"] == "CONTROL-001"
        assert set(page["items"][0]) == {
            "id",
            "patient_id",
            "case_id",
            "objective",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "current_stage",
        }
        assert client.get("/api/investigations?patient_id=OTHER").json()["total"] == 0
        assert client.get("/api/investigations?case_id=OTHER").json()["total"] == 0
        assert client.get("/api/investigations?status=completed").json()["total"] == 0
        for query in ["status=made_up", "limit=101", "offset=-1"]:
            assert client.get(f"/api/investigations?{query}").status_code == 422


async def test_document_filters_timeline_and_ownership(catalog_setup):
    settings, source, storage = catalog_setup
    await load(settings, source, storage)
    with TestClient(create_app(settings)) as client:
        base = "/api/hospital/v1/patients/PAT-CONTROL"
        notes = client.get(base + "/documents?q=Pipeline&encounter_id=ENC-CONTROL").json()
        assert notes["pagination"]["total"] == 1
        assert client.get(base + "/documents?q=absent").json()["data"] == []
        assert client.get(base + "/documents?encounter_id=OTHER&q=Pipeline").json()["data"] == []
        assert client.get(base + "/observations?q=Pipeline").status_code == 422
        assert client.get(base + "/timeline?q=Pipeline").status_code == 422
        timeline = client.get(base + "/timeline?encounter_id=ENC-CONTROL").json()["data"]
        assert timeline and all(r["encounter_id"] == "ENC-CONTROL" for r in timeline)
        assert client.get(base + "/timeline?encounter_id=OTHER").json()["data"] == []
        assert client.get(base + "/observations?encounter_id=OTHER").json()["data"] == []
        assert client.get("/api/hospital/v1/patients/OTHER/documents").status_code == 404
        assert client.get("/api/hospital/v1/documents/MISSING").status_code == 404
        assert client.get(base + "/observations/series?test_code=CONTROL").status_code == 200


async def test_catalog_releases_read_transaction_before_validation(catalog_setup, monkeypatch):
    settings, source, storage = catalog_setup
    await load(settings, source, storage)
    database = Database(settings)
    try:
        async with database.session() as session:
            original = __import__("app.hospital.catalog", fromlist=["discover_case"]).discover_case

            def checked(*args, **kwargs):
                assert not session.in_transaction()
                return original(*args, **kwargs)

            monkeypatch.setattr("app.hospital.catalog.discover_case", checked)
            result = await CaseCatalog(
                ClinicalRecordService(HospitalRepository(session)), settings
            ).items()
            assert result
    finally:
        await database.dispose()
