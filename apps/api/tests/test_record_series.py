"""Independent positive and negative longitudinal controls; no evaluation keys."""

import pytest

from app.clinical.series import record_series
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.errors import HospitalError
from app.schemas.investigation import SourceRecord, SourceRef


def observation(index, value, **overrides):
    data = dict(
        patient_id="P-SERIES",
        encounter_id=f"ENC-{index}",
        test_name="Independent analyte",
        test_code="TEST-X",
        unit="units/L",
        value_numeric=value,
        reference_range_high=10,
        reference_range_low=0,
        specimen_collected_at=f"2026-01-{index:02}T09:00:00+00:00",
        **overrides,
    )
    return SourceRecord(
        source=SourceRef(type="observation", id=f"OBS-{index}"),
        data=data,
        source_hash=digest(data),
        source_version=1,
    )


class Resolver:
    def __init__(self, rows):
        self.rows = {r.source.id: r for r in rows}

    async def resolve(self, patient, source):
        if source.id not in self.rows or self.rows[source.id].data["patient_id"] != patient:
            raise HospitalError()
        return self.rows[source.id]


async def test_repeated_abnormalities_include_intermediate_recovery_and_regenerate_claim():
    rows = [observation(1, 11), observation(2, 20), observation(3, 11)]
    (candidate,) = record_series(rows)
    assert {a.source.id for a in candidate.anchors} == {"OBS-1", "OBS-2", "OBS-3"}
    candidate.claim = "An invented diagnosis that must never be published"
    verification, claim = await EvidenceVerifier(Resolver(rows), "P-SERIES").verify(candidate)
    assert verification.status == "verified"
    assert "20" in claim and "diagnosis" not in claim
    candidate.anchors[0].expected = 999
    verification, _ = await EvidenceVerifier(Resolver(rows), "P-SERIES").verify(candidate)
    assert verification.status == "rejected"


@pytest.mark.parametrize("mutation", ["unit", "patient", "range", "encounter", "search_hit"])
def test_series_does_not_merge_incompatible_or_normal_sources(mutation):
    rows = [observation(1, 11), observation(2, 12)]
    if mutation == "search_hit":
        rows[1].representation = "search_hit"
    else:
        field, value = {
            "unit": ("unit", "other"),
            "patient": ("patient_id", "FOREIGN"),
            "range": ("reference_range_high", 100),
            "encounter": ("encounter_id", "ENC-1"),
        }[mutation]
        rows[1].data[field] = value
    assert record_series(rows) == []


def test_medication_sequence_is_not_ingestion_or_causality():
    rows = []
    for n, status in enumerate(["active", "discontinued", "active"], 1):
        data = dict(
            patient_id="P-SERIES",
            encounter_id=f"ENC-{n}",
            medication_name="Independent medication",
            status=status,
            ordered_at=f"2026-01-{n:02}T09:00:00+00:00",
        )
        rows.append(
            SourceRecord(
                source=SourceRef(type="medication", id=f"MED-{n}"),
                data=data,
                source_hash=digest(data),
                source_version=1,
            )
        )
    (candidate,) = record_series(rows)
    assert candidate.claim_kind == "observation"
    assert "ingestion" in candidate.limitations[0]
    assert all(f"MED-{n}" in candidate.claim for n in range(1, 4))
    rows[1].data["status"] = "active"
    assert record_series(rows) == []


async def test_specialist_limit_is_propagated_to_terminal_report(tmp_path, monkeypatch):
    from test_investigation import setup_case

    from app.agents.specialists import LaboratoryAgent
    from app.composition import build_engine
    from app.schemas.investigation import AgentResult, CreateInvestigation

    async def capped(self):
        return AgentResult(limitations=["Longitudinal observation limit reached."]), []

    monkeypatch.setattr(LaboratoryAgent, "run", capped)
    settings, database, store = await setup_case(tmp_path)
    try:
        identifier, _ = await store.create(CreateInvestigation(patient_id="PAT-CONTROL"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        assert report.status == "completed_with_limitations"
        assert "Longitudinal observation limit reached." in report.limitations
    finally:
        await database.dispose()
