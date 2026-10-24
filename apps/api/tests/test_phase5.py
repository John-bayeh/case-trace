"""Phase 5 adversarial verification and maintenance boundaries."""

import sys
from pathlib import Path

import pytest
from test_investigation import setup_case

from app.agents.analysis import anchor
from app.evidence.verification import EvidenceVerifier
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.schemas.investigation import Candidate, SourceRef
from app.tools.clinical import ClinicalTools

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from demo_reset import approved_target, reset  # noqa: E402


@pytest.mark.parametrize(
    "mutation",
    ["unit", "timestamp", "encounter", "quote", "duplicate", "no_support", "missing", "page"],
)
async def test_adversarial_evidence(tmp_path, mutation):
    settings, database, _ = await setup_case(tmp_path)
    try:
        tools = ClinicalTools(
            SimulatedHospitalAdapter(database, LocalAssetReader(settings.resolved_asset_path))
        )
        record = await tools.resolve("PAT-CONTROL", SourceRef(type="observation", id="LAB-CONTROL"))
        field = (
            "unit"
            if mutation == "unit"
            else "specimen_collected_at"
            if mutation == "timestamp"
            else "value_numeric"
        )
        candidate = Candidate(
            type="clinical_relationship",
            title="Adversarial",
            claim="Must not verify invalid evidence",
            claim_kind="observation",
            rule="field_observation",
            anchors=[anchor(record, field)],
        )
        a = candidate.anchors[0]
        if mutation in {"unit", "timestamp"}:
            a.expected = "forged"
        elif mutation == "encounter":
            a.encounter_id = "WRONG"
        elif mutation == "quote":
            a.quote = "invented passage"
        elif mutation == "duplicate":
            candidate.anchors.append(a.model_copy(deep=True))
        elif mutation == "no_support":
            a.relationship = "contextualizes"
        elif mutation == "missing":
            a.source.id = "MISSING"
        else:
            a.field = "pdf_page_999"
        result, _ = await EvidenceVerifier(tools, "PAT-CONTROL").verify(candidate)
        assert result.status == "rejected"
        assert any(check.status == "failed" for check in result.checks)
    finally:
        await database.dispose()


def test_reset_rejects_active_database_and_requires_offline(tmp_path):
    for path in [
        Path("relative.db"),
        ROOT / "data/runtime/casetrace.db",
        tmp_path / "arbitrary.db",
    ]:
        with pytest.raises(ValueError):
            approved_target(path)
    target = ROOT / "data/runtime/demo/casetrace-demo.db"
    assert reset(target)["dry_run"]
    with pytest.raises(ValueError, match="Stop the API"):
        reset(target, confirm=True)


async def test_reset_preserves_sources_and_clears_linked_audit_rows(tmp_path):
    from demo_reset import clear
    from sqlalchemy import text

    from app.composition import build_engine
    from app.schemas.investigation import CreateInvestigation

    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        with pytest.raises(ValueError, match="Active investigations"):
            await clear(settings)
        await build_engine(store, settings).execute(identifier)
        counts = await clear(settings)
        assert counts["investigations"] == 1
        async with database.session() as session:
            assert (await session.execute(text("SELECT count(*) FROM patients"))).scalar() == 1
            assert (await session.execute(text("SELECT count(*) FROM findings"))).scalar() == 0
        assert (await clear(settings))["investigations"] == 0
    finally:
        await database.dispose()
