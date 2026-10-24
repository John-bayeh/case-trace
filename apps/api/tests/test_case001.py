"""Offline CASE-001 acceptance; all persistence uses fresh migrated temp files."""

import hashlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

pytest.importorskip("reportlab", reason="install --group case-data for dataset acceptance")
pytest.importorskip("pymupdf", reason="install --group case-data for dataset acceptance")

from test_hospital import migrate

from app.core.config import Settings
from app.core.database import Database
from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import ImportConflict, ingest
from app.hospital.validation import validate_case
from app.main import create_app
from app.models import hospital as db

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_case001 import generate  # noqa: E402
from validate_case001 import validate  # noqa: E402


def file_hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_case001_integrity_and_reproduction(tmp_path):
    report = validate(ROOT)
    assert report["status"] == "valid"
    assert report["assets"] == 25
    assert report["pdf_pages_rendered"] >= 23
    generate(tmp_path)
    validate(tmp_path)
    # PNG compression bytes differ across linked zlib builds (Windows vs Linux),
    # even with identical decoded RGB pixels. Frozen originals still pass their
    # exact manifest checks above; only regenerated PNG encodings may differ.
    from PIL import Image

    assert (ROOT / "data/cases/CASE-001/case.json").read_bytes() == (
        tmp_path / "data/cases/CASE-001/case.json"
    ).read_bytes()
    original = json.loads((ROOT / "data/cases/CASE-001/manifest.json").read_text(encoding="utf-8"))
    recreated = json.loads(
        (tmp_path / "data/cases/CASE-001/manifest.json").read_text(encoding="utf-8")
    )
    image_ids = []
    for left, right in zip(original["assets"], recreated["assets"], strict=True):
        old_path = ROOT / "data/assets" / left["storage_path"]
        new_path = tmp_path / "data/assets" / right["storage_path"]
        if left["mime_type"].startswith("image/"):
            image_ids.append(left["id"])
            with Image.open(old_path) as old, Image.open(new_path) as new:
                assert (old.mode, old.size, old.tobytes()) == (new.mode, new.size, new.tobytes())
            for name in ["sha256", "byte_size"]:
                left.pop(name)
                right.pop(name)
        else:
            assert old_path.read_bytes() == new_path.read_bytes()
    assert original == recreated
    original_key = json.loads(
        (ROOT / "evaluation/CASE-001/answer-key.json").read_text(encoding="utf-8")
    )
    recreated_key = json.loads(
        (tmp_path / "evaluation/CASE-001/answer-key.json").read_text(encoding="utf-8")
    )
    for image_id in image_ids:
        original_key["source_checksums"].pop(image_id)
        recreated_key["source_checksums"].pop(image_id)
    assert original_key == recreated_key


@pytest.mark.parametrize("mutation", ["gold_anchor", "lab_value", "followup_time", "asset_bytes"])
def test_case001_rejects_corruption(tmp_path, mutation):
    generate(tmp_path)
    path = tmp_path / "data/cases/CASE-001/case.json"
    if mutation == "gold_anchor":
        key_path = tmp_path / "evaluation/CASE-001/answer-key.json"
        key = json.loads(key_path.read_text())
        key["expected_findings"][0]["anchors"][0]["quote"] = "NONEXISTENT CLAIM"
        key_path.write_text(json.dumps(key))
    elif mutation == "asset_bytes":
        pdf = tmp_path / "data/assets/cases/CASE-001/documents/DOC-001-01.pdf"
        pdf.write_bytes(pdf.read_bytes() + b"CORRUPTION")
    else:
        raw = json.loads(path.read_text())
        if mutation == "lab_value":
            raw["observations"][0]["value_numeric"] = 99
        else:
            raw["documents"][9]["event_at"] = "2026-04-30T09:00:00+03:00"
        path.write_text(json.dumps(raw))
        # Update the source hash so deeper semantic checks must catch it.
        manifest_path = path.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["case_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate(tmp_path)


async def test_case001_import_api_isolation_and_rollback(tmp_path):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'case001.db'}",
        asset_storage_path=ROOT / "data/assets",
    )
    migrate(settings)
    storage = LocalAssetStorage(settings.resolved_asset_path)
    source = ROOT / "data/cases/CASE-001/case.json"
    validated = validate_case(source, storage)
    database = Database(settings)
    try:
        await database.initialize()
        async with database.session() as session:
            assert (await ingest(session, validated))["status"] == "imported"
        async with database.session() as session:
            assert (await ingest(session, validated))["status"] == "unchanged"
        # A new version with a new patient but conflicting downstream public IDs
        # must undo its inserted dataset/patient as well as all later inserts.
        raw = json.loads(source.read_text())
        raw["version"] = "1.1"
        raw["patient"]["id"] = "SYN-ROLLBACK"
        for value in raw.values():
            if isinstance(value, list):
                for record in value:
                    if "patient_id" in record:
                        record["patient_id"] = "SYN-ROLLBACK"
        alternate = tmp_path / "alternate.json"
        alternate.write_text(json.dumps(raw))
        async with database.session() as session:
            with pytest.raises(ImportConflict):
                await ingest(session, validate_case(alternate, storage))
        async with database.session() as session:
            assert await session.scalar(select(func.count()).select_from(db.CaseDataset)) == 1
            assert await session.scalar(select(func.count()).select_from(db.Patient)) == 1
            assert await session.scalar(select(func.count()).select_from(db.Encounter)) == 7
            assert (await session.execute(text("PRAGMA foreign_key_check"))).all() == []
            assert (await session.execute(text("PRAGMA integrity_check"))).scalar() == "ok"
            key = json.loads((ROOT / "evaluation/CASE-001/answer-key.json").read_text())
            for table in db.Base.metadata.sorted_tables:
                rows = str((await session.execute(select(table))).all())
                assert key["expected_findings"][0]["expected_claim"] not in rows
                assert "expected_findings" not in rows
                assert "ground_truth_interpretation" not in rows
    finally:
        await database.dispose()

    prefix = "/api/hospital/v1"
    with TestClient(create_app(settings)) as client:
        assert (
            client.get(prefix + "/patients/SYN-001").json()["data"]["display_name"]
            == "Daniel M. (synthetic)"
        )
        counts = {
            "encounters": 7,
            "clinical-events": 8,
            "observations": 25,
            "medications": 7,
            "documents": 23,
            "imaging-studies": 3,
            "referrals": 2,
            "diagnoses": 3,
            "symptoms": 1,
            "diagnostic-reports": 8,
        }
        for resource, count in counts.items():
            response = client.get(f"{prefix}/patients/SYN-001/{resource}?limit=100")
            assert response.status_code == 200, response.text
            assert len(response.json()["data"]) == count
            assert "expected_findings" not in response.text
            assert "ground_truth_interpretation" not in response.text
        key = json.loads((ROOT / "evaluation/CASE-001/answer-key.json").read_text())
        for record_id in key["expected_findings"][0]["required_source_ids"]:
            kind = "documents" if record_id.startswith("DOC") else "medications"
            response = client.get(f"{prefix}/{kind}/{record_id}")
            assert response.status_code == 200
            assert response.json()["data"]["id"] == record_id
        for doc in validated.clinical.documents:
            response = client.get(f"{prefix}/documents/{doc.id}/asset")
            assert response.status_code == 200
            assert hashlib.sha256(response.content).hexdigest() == validated.assets[doc.id].sha256
        for asset in validated.clinical.imaging_assets:
            response = client.get(f"{prefix}/imaging-assets/{asset.id}/content")
            assert response.status_code == 200
            assert hashlib.sha256(response.content).hexdigest() == validated.assets[asset.id].sha256
        for study_id, asset_id in [
            ("IMG-001-01", "IMG-ASSET-001-01"),
            ("IMG-001-02", "IMG-ASSET-001-02"),
        ]:
            assets = client.get(f"{prefix}/imaging-studies/{study_id}/assets")
            assert assets.status_code == 200
            assert [item["id"] for item in assets.json()["data"]] == [asset_id]
            assert assets.json()["data"][0]["mime_type"] == "image/jpeg"
        report_only = client.get(f"{prefix}/imaging-studies/IMG-001-03/assets")
        assert report_only.status_code == 200
        assert report_only.json()["data"] == []
        assert client.get(f"{prefix}/imaging-studies/IMG-001-03/report").status_code == 200
        assert client.get(f"{prefix}/documents/answer-key/asset").status_code == 404
        assert client.get("/evaluation/CASE-001/answer-key.json").status_code == 404
