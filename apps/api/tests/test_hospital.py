"""Hospital pipeline control; deliberately unrelated to the absent CASE-001."""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.config import Settings
from app.core.database import Database
from app.hospital.assets import AssetError, LocalAssetStorage
from app.hospital.ingestion import ImportConflict, ingest
from app.hospital.validation import CaseValidationError, validate_case
from app.main import create_app
from app.models import hospital as db

FIXTURE = Path(__file__).parent / "fixtures" / "control-case.json"
API_ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "EVALUATION_SENTINEL_NEVER_SERVE"


def migrate(settings: Settings) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env={**os.environ, "DATABASE_URL": str(settings.resolved_database_url)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Settings, Path, LocalAssetStorage]:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'hospital.db'}",
        asset_storage_path=tmp_path / "assets",
    )
    asset = settings.resolved_asset_path / "cases" / "CONTROL-001" / "control.txt"
    asset.parent.mkdir(parents=True)
    asset.write_text("SYNTHETIC — NOT FOR CLINICAL USE. Pipeline control.\n")
    source = tmp_path / "case.json"
    source.write_bytes(FIXTURE.read_bytes())
    migrate(settings)
    return settings, source, LocalAssetStorage(settings.resolved_asset_path)


async def load(settings: Settings, source: Path, storage: LocalAssetStorage) -> dict[str, object]:
    database = Database(settings)
    try:
        await database.initialize()
        async with database.session() as session:
            return await ingest(session, validate_case(source, storage))
    finally:
        await database.dispose()


async def test_import_idempotency_provenance_and_ground_truth(setup):
    settings, source, storage = setup
    original = source.read_bytes()
    assert (await load(settings, source, storage))["status"] == "imported"
    assert (await load(settings, source, storage))["status"] == "unchanged"
    assert source.read_bytes() == original
    database = Database(settings)
    try:
        async with database.session() as session:
            assert await session.scalar(select(func.count()).select_from(db.Patient)) == 1
            lab = await session.scalar(select(db.LabResult))
            assert lab.collected_at == datetime(2026, 1, 1, 6, 10, tzinfo=UTC)
            assert lab.reported_at != lab.collected_at
            assert lab.source_document_id is not None
            med = await session.scalar(select(db.MedicationEvent))
            assert med.effective_at is None
            assert med.payload["start_at"] == "2026-01-02"
            for table in db.Base.metadata.sorted_tables:
                rows = (await session.execute(select(table))).all()
                assert SENTINEL not in str(rows)
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "change,expected",
    [
        (lambda r: r["observations"][0].update(source_document_id="MISSING"), "source document"),
        (lambda r: r["observations"][0].update(encounter_id="MISSING"), "encounter_id"),
        (lambda r: r["observations"][0].update(patient_id="OTHER"), "patient_id"),
        (lambda r: r["observations"][0].update(value_numeric=None), "needs a value"),
        (lambda r: r["observations"][0].update(invented_field="bad"), "Extra inputs"),
        (lambda r: r["observations"][0].update(reported_at="2025-01-01T00:00:00Z"), "precedes"),
        (lambda r: r["encounters"][0].update(started_at="2026-01-01T09:00:00"), "UTC offset"),
        (lambda r: r["documents"][0].update(storage_path="../answer.json"), "unsafe"),
        (
            lambda r: r["documents"][0].update(storage_path="cases/CONTROL-001/missing.pdf"),
            "missing",
        ),
        (
            lambda r: r["documents"][0].update(
                storage_path="cases/CONTROL-001/expected/answer.txt"
            ),
            "evaluation",
        ),
        (lambda r: r["medications"][0].update(id="LAB-CONTROL"), "duplicate"),
        (lambda r: r["diagnoses"][0].update(unknown="bad"), "Extra inputs"),
    ],
)
def test_validation_failures(setup, change, expected):
    _, source, storage = setup
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    change(raw)
    source.write_text(json.dumps(raw))
    with pytest.raises(CaseValidationError, match=expected):
        validate_case(source, storage)


async def test_changed_import_and_atomic_rollback(setup):
    settings, source, storage = setup
    await load(settings, source, storage)
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    raw["patient"]["display_name"] = "Different Synthetic Control"
    source.write_text(json.dumps(raw))
    with pytest.raises(ImportConflict, match="different clinical content"):
        await load(settings, source, storage)
    # Different dataset and patient, same encounter ID: failure occurs after inserting
    # dataset/patient. The entire transaction must roll back, then a retry can work.
    raw["case_id"] = "CONTROL-002"
    raw["documents"][0]["storage_path"] = None
    old = raw["patient"]["id"]
    raw["patient"]["id"] = "PAT-CONTROL-2"
    for group in raw.values():
        if isinstance(group, list):
            for row in group:
                if row.get("patient_id") == old:
                    row["patient_id"] = raw["patient"]["id"]
    source.write_text(json.dumps(raw))
    with pytest.raises(ImportConflict, match="rolled back"):
        await load(settings, source, storage)
    database = Database(settings)
    try:
        async with database.session() as session:
            assert await session.scalar(select(func.count()).select_from(db.CaseDataset)) == 1
            assert await session.scalar(select(func.count()).select_from(db.Patient)) == 1
    finally:
        await database.dispose()
    # Remove collision-bearing clinical rows; the retry imports the valid patient.
    for key in [
        "encounters",
        "documents",
        "observations",
        "medications",
        "clinical_events",
        "imaging_studies",
        "referrals",
        "diagnoses",
        "symptoms",
        "diagnostic_reports",
    ]:
        raw[key] = []
    source.write_text(json.dumps(raw))
    assert (await load(settings, source, storage))["status"] == "imported"


async def test_deterministic_clean_import(setup, tmp_path):
    settings, source, storage = setup
    other = settings.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{tmp_path / 'second.db'}"}
    )
    migrate(other)
    await load(settings, source, storage)
    await load(other, source, storage)
    snapshots = []
    for config in [settings, other]:
        database = Database(config)
        try:
            async with database.session() as session:
                snapshots.append(
                    {
                        table.name: [
                            tuple(
                                value for key, value in row._mapping.items() if key != "seeded_at"
                            )
                            for row in (
                                await session.execute(
                                    select(table).order_by(*table.primary_key.columns)
                                )
                            ).all()
                        ]
                        for table in db.Base.metadata.sorted_tables
                    }
                )
        finally:
            await database.dispose()
    assert snapshots[0] == snapshots[1]


async def test_database_constraints_and_utc(setup):
    settings, source, storage = setup
    await load(settings, source, storage)
    database = Database(settings)
    try:
        async with database.session() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text("UPDATE lab_results SET encounter_id = :bad"), {"bad": uuid4().hex}
                    )
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(text("UPDATE patients SET is_synthetic = 0"))
            with pytest.raises(StatementError):
                async with session.begin():
                    lab = await session.scalar(select(db.LabResult))
                    lab.collected_at = datetime(2026, 1, 1)
                    await session.flush()
            async with session.begin():
                assert (await session.execute(text("PRAGMA foreign_key_check"))).all() == []
    finally:
        await database.dispose()


async def test_hospital_api_pipeline(setup):
    settings, source, storage = setup
    await load(settings, source, storage)
    with TestClient(create_app(settings)) as client:
        prefix = "/api/hospital/v1"
        patients = client.get(f"{prefix}/patients?query=CONTROL&limit=1").json()
        assert patients["data"][0]["id"] == "PAT-CONTROL"
        assert patients["pagination"] == {"limit": 1, "offset": 0, "total": 1, "has_more": False}
        for resource in [
            "encounters",
            "observations",
            "medications",
            "documents",
            "clinical-events",
            "imaging-studies",
            "referrals",
            "timeline",
        ]:
            response = client.get(f"{prefix}/patients/PAT-CONTROL/{resource}")
            assert response.status_code == 200, response.text
            assert response.json()["data"]
            assert SENTINEL not in response.text
            assert "storage_path" not in response.text
        document = client.get(f"{prefix}/documents/DOC-CONTROL").json()["data"]
        assert "Pipeline control record" in document["text_content"]
        assert document["event_at"] != document["authored_at"]
        assert (
            client.get(f"{prefix}/documents/DOC-CONTROL/asset")
            .headers["content-type"]
            .startswith("text/plain")
        )
        assert client.get(f"{prefix}/imaging-studies/IMG-CONTROL/report").status_code == 200
        assert (
            client.get(f"{prefix}/patients/PAT-CONTROL/summary").json()["data"]["encounter_count"]
            == 1
        )
        timeline = client.get(f"{prefix}/patients/PAT-CONTROL/timeline").json()["data"]
        assert all(e["source_ref"]["id"] != "MED-CONTROL" for e in timeline)
        assert (
            client.get(f"{prefix}/patients/PAT-CONTROL/observations?test_code=absent").json()[
                "data"
            ]
            == []
        )
        assert client.get(f"{prefix}/patients/PAT-CONTROL/observations?limit=0").status_code == 422
        assert (
            client.get(
                f"{prefix}/patients/PAT-CONTROL/observations?start_at=2026-01-01T09:00:00"
            ).status_code
            == 422
        )
        for path in [
            "patients/missing",
            "documents/missing",
            "patients/PAT-OTHER/observations",
            "ground_truth",
            "documents/expected/asset",
        ]:
            response = client.get(f"{prefix}/{path}")
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
            assert "request_id" in response.json()["meta"]
        # Missing and changed assets must never appear as successful content.
        asset = storage.resolve("cases/CONTROL-001/control.txt", "CONTROL-001")
        asset.write_text("modified")
        assert client.get(f"{prefix}/documents/DOC-CONTROL/asset").status_code == 409
        asset.unlink()
        missing = client.get(f"{prefix}/documents/DOC-CONTROL/asset")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "ASSET_UNAVAILABLE"


def test_asset_symlink_escape(setup, tmp_path):
    _, _, storage = setup
    secret = tmp_path / "private.txt"
    secret.write_text(SENTINEL)
    link = storage.root / "cases/CONTROL-001/escape.txt"
    try:
        link.symlink_to(secret)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip(
                "Windows requires Developer Mode or symlink privilege for this security test"
            )
        raise
    with pytest.raises(AssetError, match="escapes"):
        storage.resolve("cases/CONTROL-001/escape.txt", "CONTROL-001")


@pytest.mark.parametrize(
    "change, expected",
    [
        (
            lambda r: r["documents"][0].update(metadata={"expected_answer": SENTINEL}),
            "metadata key",
        ),
        (
            lambda r: r["diagnostic_reports"][0].update(observation_ids=["MISSING"]),
            "observation MISSING",
        ),
        (lambda r: r["diagnostic_reports"][0].update(document_id="MISSING"), "document_id"),
        (lambda r: r["imaging_studies"][0].update(report_document_id="MISSING"), "source document"),
        (lambda r: r["diagnoses"][0].update(status="active"), "Input should be"),
    ],
)
def test_provenance_validation(setup, change, expected):
    _, source, storage = setup
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    change(raw)
    source.write_text(json.dumps(raw))
    with pytest.raises(CaseValidationError, match=expected):
        validate_case(source, storage)


async def test_synthetic_image_and_mime_integrity(setup):
    import base64

    settings, source, storage = setup
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    key = "cases/CONTROL-001/illustration.png"
    # A 1px test image, not medical evidence or a generated clinical study.
    content = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB9sAAAAASUVORK5CYII="
    )
    (storage.root / key).write_bytes(content)
    raw["imaging_assets"] = [
        {
            "id": "IMAGE-CONTROL",
            "imaging_study_id": "IMG-CONTROL",
            "asset_type": "synthetic_illustration",
            "mime_type": "image/png",
            "storage_path": key,
            "metadata": {
                "width": 1,
                "height": 1,
                "synthetic_label": "SYNTHETIC — NOT FOR CLINICAL USE",
            },
        }
    ]
    source.write_text(json.dumps(raw))
    await load(settings, source, storage)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/hospital/v1/imaging-studies/IMG-CONTROL/assets")
        assert response.status_code == 200
        assert response.json()["data"][0]["width"] == 1
        assert "storage_path" not in response.text
        response = client.get("/api/hospital/v1/imaging-assets/IMAGE-CONTROL/content")
        assert response.content == content
        assert response.headers["content-type"] == "image/png"
        assert response.headers["x-content-type-options"] == "nosniff"
    (storage.root / key).write_text("not a png")
    with pytest.raises(CaseValidationError, match="declared media type"):
        validate_case(source, storage)


async def test_cross_patient_foreign_key(setup):
    settings, source, storage = setup
    await load(settings, source, storage)
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    second = json.loads(json.dumps(raw).replace("CONTROL", "SECOND"))
    second["documents"][0]["storage_path"] = None
    source.write_text(json.dumps(second))
    await load(settings, source, storage)
    database = Database(settings)
    try:
        async with database.session() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    await session.execute(
                        text(
                            "UPDATE lab_results SET encounter_id="
                            "(SELECT id FROM encounters WHERE external_id='ENC-SECOND') "
                            "WHERE external_id='LAB-CONTROL'"
                        )
                    )
    finally:
        await database.dispose()


async def test_convenience_endpoints_and_strict_filters(setup):
    settings, source, storage = setup
    await load(settings, source, storage)
    with TestClient(create_app(settings)) as client:
        prefix = "/api/hospital/v1"
        response = client.get(f"{prefix}/encounters/ENC-CONTROL/records")
        assert response.json()["data"]["observation_ids"] == ["LAB-CONTROL"]
        response = client.get(
            f"{prefix}/patients/PAT-CONTROL/observations/series?test_code=CONTROL"
        )
        assert response.json()["data"]["points"][0]["value_numeric"] == 7
        response = client.get(f"{prefix}/patients/PAT-CONTROL/documents/search?q=pipeline")
        assert response.json()["data"][0]["id"] == "DOC-CONTROL"
        for resource in ["diagnoses", "symptoms", "diagnostic-reports"]:
            response = client.get(f"{prefix}/patients/PAT-CONTROL/{resource}")
            assert response.status_code == 200, response.text
            assert response.json()["data"]
            assert SENTINEL not in response.text
        assert (
            client.get(f"{prefix}/patients/PAT-CONTROL/observations?unknown=bad").status_code == 422
        )
        response = client.get(
            f"{prefix}/patients/PAT-CONTROL/observations",
            params={"start_at": "2026-01-03T00:00:00Z", "end_at": "2026-01-01T00:00:00Z"},
        )
        assert response.status_code == 422
