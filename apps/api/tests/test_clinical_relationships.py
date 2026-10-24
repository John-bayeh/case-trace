"""Independent relationship controls. No answer keys or canonical case mutations."""

import json
from pathlib import Path

import pytest

from app.clinical.extraction import extract_claims
from app.clinical.relationship_synthesis import synthesize_relationships
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.errors import HospitalError
from app.hospital.schemas import Medication
from app.schemas.investigation import Candidate, SourceRecord, SourceRef


def medication(
    identifier="ORDER-A",
    status="discontinued",
    when="2024-02-01T10:00:00+02:00",
    encounter="VISIT-A",
    name="Control medication",
):
    data = Medication(
        id=identifier,
        patient_id="SYN-RELATIONSHIP",
        encounter_id=encounter,
        medication_name=name,
        generic_name=name,
        status=status,
        ordered_at=when,
    ).model_dump(mode="json")
    return SourceRecord(
        source={"type": "medication", "id": identifier},
        source_version=1,
        source_hash=digest(data),
        data=data,
    )


class Resolver:
    """Deliberately permissive owner handling exercises verifier defense in depth."""

    def __init__(self, rows):
        self.rows = {(r.source.type, r.source.id): r for r in rows}
        self.calls = []

    async def resolve(self, patient_id, source):
        self.calls.append((patient_id, source.id))
        row = self.rows.get((source.type, source.id))
        if row is None:
            raise HospitalError()
        return row


def pair():
    rows = [medication(), medication("ORDER-B", "active", "2024-03-01T10:00:00+02:00", "VISIT-B")]
    (candidate,) = synthesize_relationships(rows)
    return rows, candidate


async def check(candidate, rows):
    return await EvidenceVerifier(Resolver(rows), "SYN-RELATIONSHIP").verify(candidate)


async def test_cross_encounter_record_relationship_is_canonical_and_versioned():
    rows, candidate = pair()
    assert candidate.relationship
    assertions = candidate.relationship.assertions
    assert [a.origin for a in assertions] == ["order", "order"]
    assert [a.source_status for a in assertions] == ["discontinued", "active"]
    assert assertions[0].event_time_field == "ordered_at"
    assert assertions[0].documentation_time_field is None
    assert assertions[0].timestamps["ordered_at"] == rows[0].data["ordered_at"]
    # Candidate prose is not evidence; only the canonical proposition can publish.
    original = candidate.claim
    candidate.claim = "These records prove ingestion and a definitive causal diagnosis."
    verdict, canonical = await check(candidate, rows)
    assert verdict.status == "verified"
    assert canonical == original
    assert "does not establish" in canonical
    assert all(a.anchor.source_version == 1 for a in assertions)
    assert Candidate.model_validate_json(candidate.model_dump_json()) == candidate


@pytest.mark.parametrize(
    "attack",
    [
        "wrong_patient",
        "source_version",
        "source_hash",
        "missing_source",
        "altered_field",
        "source_type",
        "search_hit",
        "bad_dto_hash",
        "offset",
    ],
)
async def test_source_and_citation_integrity(attack):
    rows, candidate = pair()
    if attack == "wrong_patient":
        rows[0].data["patient_id"] = "OTHER-PATIENT"
        rows[0].source_hash = digest(rows[0].data)
    elif attack == "source_version":
        rows[0].source_version = 2
    elif attack == "source_hash":
        candidate.anchors[0].source_hash = "0" * 64
    elif attack == "missing_source":
        rows.pop()
    elif attack == "altered_field":
        candidate.anchors[0].expected = "administered"
    elif attack == "source_type":
        candidate.anchors[0].source.type = "document"
    elif attack == "search_hit":
        rows[0].representation = "search_hit"
    elif attack == "bad_dto_hash":
        rows[0].data["status"] = "held"
    else:
        candidate.anchors[0].quote = "discontinued"
        candidate.anchors[0].char_start = 1
        candidate.anchors[0].char_end = 13
    assert (await check(candidate, rows))[0].status == "rejected"


@pytest.mark.parametrize(
    "field,value",
    [
        ("value", "administered"),
        ("concept", "Different medication"),
        ("origin", "observation"),
        ("polarity", "negative"),
        ("certainty", "uncertain"),
        ("subject", "family"),
        ("source_status", "completed"),
        ("event_time_field", "start_at"),
    ],
)
async def test_assertions_are_reconstructed_not_trusted(field, value):
    rows, candidate = pair()
    setattr(candidate.relationship.assertions[0], field, value)
    verdict, _ = await check(candidate, rows)
    assert verdict.status == "rejected"
    assert verdict.checks[-1].type == "assertion_reconstruction"


async def test_false_and_missing_chronology():
    rows, candidate = pair()
    ordering = candidate.relationship.temporal_ordering[0]
    ordering.earlier_assertion_id, ordering.later_assertion_id = (
        ordering.later_assertion_id,
        ordering.earlier_assertion_id,
    )
    assert (await check(candidate, rows))[0].status == "rejected"
    rows, candidate = pair()
    candidate.relationship.temporal_ordering[0].earlier_field = "start_at"
    assert (await check(candidate, rows))[0].status == "inconclusive"
    rows, candidate = pair()
    candidate.relationship.temporal_ordering = []
    assert (await check(candidate, rows))[0].status == "rejected"


@pytest.mark.parametrize("intent", ["ingestion", "causality", "diagnosis"])
async def test_unsupported_medical_conclusions_rejected(intent):
    rows, candidate = pair()
    candidate.relationship.conclusion_kind = intent
    assert (await check(candidate, rows))[0].status == "rejected"


@pytest.mark.parametrize(
    "kind",
    [
        "medication_reconciliation",
        "result_followup",
        "hypothesis_challenge",
        "longitudinal_followup",
    ],
)
async def test_unimplemented_clinical_meaning_is_inconclusive(kind):
    rows, candidate = pair()
    candidate.relationship.relationship_type = kind
    candidate.relationship.conclusion_kind = "interpretation"
    verdict, canonical = await check(candidate, rows)
    assert verdict.status == "inconclusive"
    assert "not established" in canonical
    assert any(
        c.type == "assertion_reconstruction" and c.status == "passed" for c in verdict.checks
    )


async def test_missing_decisive_anchor_and_duplicate_assertions():
    rows, candidate = pair()
    candidate.anchors = [a for a in candidate.anchors if a.field != "ordered_at"]
    assert (await check(candidate, rows))[0].status == "rejected"
    rows, candidate = pair()
    candidate.relationship.assertions.append(
        candidate.relationship.assertions[0].model_copy(deep=True)
    )
    assert (await check(candidate, rows))[0].status == "rejected"


async def test_same_proposed_claim_cannot_connect_incompatible_records():
    rows, candidate = pair()
    rows[1] = medication(
        "ORDER-B", "active", "2024-03-01T10:00:00+02:00", "VISIT-B", "Different medication"
    )
    # Even fully valid replacement citations and assertions do not establish identity.
    replacement = extract_claims(rows[1])[0]
    old = candidate.relationship.assertions[1]
    candidate.relationship.assertions[1] = replacement
    candidate.relationship.supporting_assertion_ids[1] = replacement.id
    candidate.relationship.temporal_ordering[0].later_assertion_id = replacement.id
    for a in candidate.anchors:
        if a.source.id == rows[1].source.id:
            a.source_hash = rows[1].source_hash
            a.expected = rows[1].data[a.field]
    assert old.concept != replacement.concept
    assert (await check(candidate, rows))[0].status == "rejected"


async def test_same_display_name_with_incompatible_medication_identity_is_not_connected():
    rows, candidate = pair()
    rows[1].data["generic_name"] = "Different active ingredient"
    rows[1].source_hash = digest(rows[1].data)
    replacement = extract_claims(rows[1])[0]
    candidate.relationship.assertions[1] = replacement
    candidate.relationship.supporting_assertion_ids[1] = replacement.id
    candidate.relationship.temporal_ordering[0].later_assertion_id = replacement.id
    for a in candidate.anchors:
        if a.source.id == rows[1].source.id:
            a.source_hash = rows[1].source_hash
            a.expected = rows[1].data[a.field]
    assert candidate.relationship.assertions[0].concept == replacement.concept
    assert (await check(candidate, rows))[0].status == "rejected"


async def test_current_version_and_timezone_order_are_preserved():
    rows = [medication(), medication("ORDER-B", "active", "2024-02-01T09:30:00+00:00", "VISIT-B")]
    for row in rows:
        row.source_version = 2
    (candidate,) = synthesize_relationships(rows)
    verdict, _ = await check(candidate, rows)
    assert verdict.status == "verified"
    assert all(a.source_version == 2 for a in candidate.anchors)


def test_assertion_origin_keeps_reports_and_interpretations_distinct():
    rows = chronology_sources()
    claims = extract_claims(rows[1])
    assert claims[0].origin == "patient_report"
    assert claims[0].documentation_time_field == "documented_at"
    assert claims[0].timestamps["documented_at"] != claims[0].timestamps["occurred_at"]
    rows[1].data["description"] = "Clinician reports cough."
    rows[1].source_hash = digest(rows[1].data)
    assert extract_claims(rows[1])[0].origin == "clinician_record"


def test_relationship_caps_and_role_reference_validation():
    rows = [
        medication(
            f"ORDER-{n}",
            "active" if n % 2 else "held",
            f"2024-03-{n + 1:02}T10:00:00+02:00",
            f"VISIT-{n}",
        )
        for n in range(20)
    ]
    assert len(synthesize_relationships(rows, states_only=True)) == 8
    _, candidate = pair()
    data = candidate.model_dump()
    data["relationship"]["contradicting_assertion_ids"] = ["UNKNOWN"]
    with pytest.raises(ValueError, match="evidence role"):
        Candidate.model_validate(data)


def chronology_sources():
    sources = []
    for kind, identifier, data in [
        (
            "document",
            "HISTORY-LATER",
            {
                "text_content": "Cough first began on August 20, 2024; no cough before then.",
                "event_at": "2024-08-25T10:00:00+02:00",
                "authored_at": "2024-08-25T11:00:00+02:00",
                "encounter_id": "VISIT-LATER",
            },
        ),
        (
            "clinical_event",
            "EVENT-EARLIER",
            {
                "description": "Patient reports cough.",
                "occurred_at": "2024-08-02T09:00:00+02:00",
                "documented_at": "2024-08-02T10:00:00+02:00",
                "encounter_id": "VISIT-EARLIER",
            },
        ),
    ]:
        data.update(id=identifier, patient_id="SYN-RELATIONSHIP")
        sources.append(
            SourceRecord(
                source={"type": kind, "id": identifier},
                source_version=1,
                source_hash=digest(data),
                data=data,
            )
        )
    return sources


async def test_conflicting_documentation_preserves_both_roles_and_uncertainty():
    rows = chronology_sources()
    candidate = next(
        c
        for c in synthesize_relationships(rows)
        if c.relationship.relationship_type == "documented_assertion_conflict"
    )
    verdict, canonical = await check(candidate, rows)
    assert verdict.status == "verified"
    assert {a.relationship for a in candidate.anchors} >= {"supports", "contradicts"}
    assert "true onset" in canonical
    original = candidate.relationship.assertions[1].anchor.source.id
    assert any(
        a.source.id == original and a.relationship == "contradicts" for a in candidate.anchors
    )
    candidate.anchors = [
        a.model_copy(update={"relationship": "supports"}) for a in candidate.anchors
    ]
    assert (await check(candidate, rows))[0].status == "rejected"


async def test_late_documentation_does_not_become_verified_conflict():
    rows = chronology_sources()
    candidate = synthesize_relationships(rows)[0]
    rows[1].data["documented_at"] = "2024-09-01T10:00:00+02:00"
    rows[1].source_hash = digest(rows[1].data)
    assert not synthesize_relationships(rows)
    assert (await check(candidate, rows))[0].status == "rejected"


def test_search_hits_same_encounter_duplicate_records_and_equal_times_do_not_assemble():
    first = medication()
    assert synthesize_relationships([first, first.model_copy(deep=True)]) == []
    assert synthesize_relationships([first, medication("ORDER-B", "active")]) == []
    assert (
        synthesize_relationships([first, medication("ORDER-B", "active", encounter="VISIT-B")])
        == []
    )
    second = medication("ORDER-B", "active", "2024-03-01T10:00:00+02:00", "VISIT-B")
    second.representation = "search_hit"
    assert synthesize_relationships([first, second]) == []


async def test_relationship_cannot_bypass_verification_using_legacy_rule():
    rows, candidate = pair()
    candidate.rule = "field_observation"
    assert (await check(candidate, rows))[0].status == "rejected"


def test_old_candidate_json_remains_readable():
    root = Path(__file__).resolve().parents[3]
    report = json.loads(
        (root / "docs/evaluation/artifacts/generalization/after/CASE-001/report.json").read_text()
    )
    finding = report["verified_findings"][0]
    candidate = Candidate.model_validate(
        {k: v for k, v in finding.items() if k in Candidate.model_fields}
    )
    assert candidate.relationship is None
    assert SourceRef(type="medication", id="ORDER-A").id == "ORDER-A"


async def test_existing_engine_persists_relationship_sources_and_bounded_activity(tmp_path):
    from test_investigation import setup_case

    from app.composition import build_engine
    from app.schemas.investigation import CreateInvestigation, Finding, Report

    settings, database, store = await setup_case(tmp_path, True)
    settings.investigation_reasoning = "structured"
    try:
        run, _ = await store.create(CreateInvestigation(patient_id="SYN-001"), None)
        await build_engine(store, settings).execute(run)
        report = await store.report(run)
        assert report.status == "completed", report
        relationships = [f for f in report.verified_findings if f.relationship]
        assert relationships
        events = await store.events(run, 0, 1000)
        assembled = [e for e in events if e.type == "relationship.assembled"]
        proposed = [e for e in events if e.type == "relationship.proposed"]
        completed = [e for e in events if e.type == "relationship.verification_completed"]
        assert 0 < len(assembled) <= 8
        assert len(proposed) == len(completed) == len(relationships)
        assert {e.payload["finding_id"] for e in completed} == {f.id for f in relationships}
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        assert not any(
            "quote" in e.payload or "claim" in e.payload for e in assembled + proposed + completed
        )
        traces = await store.queries.tools(run, 1000, 0)
        retrieved = {r.id for t in traces.items if t.status == "succeeded" for r in t.source_refs}
        persisted = await store.findings(run)
        for finding in relationships:
            assert {a.source.id for a in finding.anchors} <= retrieved
            assert Finding.model_validate_json(finding.model_dump_json()) == finding
            assert any(
                f.id == finding.id and f.relationship == finding.relationship for f in persisted
            )
            assert finding.relationship.unresolved_questions
            assert "do not prove ingestion" in " ".join(finding.limitations)
        # The existing report/REST representation retains the typed constituents.
        assert Report.model_validate_json(report.model_dump_json()) == report
        assert any(f.type == "timeline_contradiction" for f in report.verified_findings)
        # Finalized runs retain the established immutable persistence boundary.
        from app.orchestration.state import RunConflict

        with pytest.raises(RunConflict):
            await store.save_finding(run, relationships[0])
        assert len(await store.findings(run)) == len(persisted)
    finally:
        await database.dispose()
