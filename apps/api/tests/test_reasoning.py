"""Independent synthetic narratives; expectations live here, never in runtime tools."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agents.analysis import followups, lab_changes, medication_observations
from app.clinical.comparison import compare_claims
from app.clinical.extraction import extract_claims, validate_model_claim
from app.clinical.reasoning import structured_contradictions
from app.clinical.temporal import narrative_time
from app.core.provenance import digest
from app.evidence.provenance import anchor_matches
from app.evidence.verification import EvidenceVerifier
from app.hospital.errors import HospitalError
from app.schemas.investigation import Anchor, SourceRecord, SourceRef

NARRATIVES = json.loads((Path(__file__).parent / "fixtures/reasoning-narratives.json").read_text())


def record(text, id_="NOTE-A", kind="document", **overrides):
    data = {
        "patient_id": "SYN-INDEPENDENT",
        "encounter_id": "VISIT-A",
        "text_content" if kind == "document" else "description": text,
        **(
            {"event_at": "2024-08-25T10:00:00+02:00", "authored_at": "2024-08-25T11:00:00+02:00"}
            if kind == "document"
            else {
                "occurred_at": "2024-08-02T09:00:00+02:00",
                "documented_at": "2024-08-02T10:00:00+02:00",
            }
        ),
        **overrides,
    }
    return SourceRecord(
        source=SourceRef(type=kind, id=id_), source_version=1, source_hash=digest(data), data=data
    )


def scenario(name):
    a, b = NARRATIVES[name]
    return record(a), record(b, "EVENT-B", "clinical_event")


class Resolver:
    def __init__(self, rows):
        self.rows = {r.source.id: r for r in rows}

    async def resolve(self, patient_id, source):
        row = self.rows.get(source.id)
        if row is None or row.data["patient_id"] != patient_id or row.source != source:
            raise HospitalError("SOURCE_NOT_FOUND", 404)
        return row


@pytest.mark.parametrize("name,conflicts", [(x, int(x in "ABJK")) for x in NARRATIVES])
async def test_independent_scenarios(name, conflicts):
    note, event = scenario(name)
    findings = structured_contradictions([note], [event])
    assert len(findings) == conflicts
    for candidate in findings:
        result, claim = await EvidenceVerifier(
            Resolver([note, event]), "SYN-INDEPENDENT", "structured"
        ).verify(candidate)
        assert result.status == "verified"
        assert claim == candidate.claim
        assert all(
            anchor_matches(next(r for r in [note, event] if r.source == a.source), a)
            for a in candidate.anchors
        )
    if name == "C":
        claim = extract_claims(note)[0]
        assert claim.time.precision == "month"
        assert (claim.time.start, claim.time.end) == (date(2024, 8, 21), date(2024, 8, 31))
    if name == "D":
        assert extract_claims(event)[0].episode_scope == "recurrent"
    if name == "E":
        assert extract_claims(event)[0].polarity == "negative"
    if name == "F":
        assert extract_claims(event)[0].temporality == "historical"
    if name == "G":
        assert extract_claims(note)[0].certainty == "hypothetical"
        assert extract_claims(event)[0].subject == "family"
    if name == "K":
        candidate = findings[0].model_copy(deep=True)
        candidate.anchors[0].quote = "A fabricated clinical passage"
        result, _ = await EvidenceVerifier(
            Resolver([note, event]), "SYN-INDEPENDENT", "structured"
        ).verify(candidate)
        assert result.status == "rejected"


@pytest.mark.parametrize(
    "text,concept,polarity,assertion",
    [
        ("Patient denies cough.", "cough", "negative", "absence"),
        ("No cough today.", "cough", "negative", "absence"),
        ("Cough resolved last month.", "cough", "negative", "resolution"),
        ("Denies fever; cough persists.", "cough", "positive", "presence"),
        ("Cough is worsening.", "cough", "positive", "worsening"),
        ("Chest tightness persists.", "chest tightness", "positive", "presence"),
        ("Shortness of breath noted.", "shortness of breath", "positive", "presence"),
    ],
)
def test_assertion_context(text, concept, polarity, assertion):
    row = record(text)
    claim = next(c for c in extract_claims(row) if c.concept == concept)
    assert (claim.polarity, claim.assertion) == (polarity, assertion)
    assert anchor_matches(row, claim.anchor)
    assert claim.anchor.quote == text


@pytest.mark.parametrize(
    "transform", ["capitalization", "order", "unrelated", "ids", "paraphrase", "split"]
)
def test_meaning_preserving_transformations(transform):
    note, event = scenario("A")
    notes, events = [note], [event]
    if transform == "capitalization":
        notes = [record(NARRATIVES["A"][0].upper())]
    elif transform == "order":
        notes = [record("Routine appointment.", "OTHER"), note][::-1]
    elif transform == "unrelated":
        notes.append(record("Nausea resolved.", "OTHER"))
    elif transform == "ids":
        notes = [record(NARRATIVES["A"][0], "RENAMED")]
        events = [record(NARRATIVES["A"][1], "NEW-ID", "clinical_event")]
    elif transform == "paraphrase":
        notes = [record("Patient first noticed headache on August 18, 2024.")]
    elif transform == "split":
        notes = [
            record("Headache first started on August 18, 2024. No previous episodes reported.")
        ]
    assert len(structured_contradictions(notes, events)) == 1


def test_meaning_changing_transformations():
    note, event = scenario("B")
    assert not structured_contradictions([record("Cough began around August 18, 2024.")], [event])
    assert not structured_contradictions(
        [note], [record("Denies cough.", "EVENT-B", "clinical_event")]
    )
    historical = record("Had a similar cough in July.", "HISTORICAL", "clinical_event")
    assert len(structured_contradictions([note], [historical, event])) == 1
    assert not structured_contradictions([note], [historical])


def test_relative_unknown_and_invalid_dates():
    value = narrative_time(
        "Cough started about two weeks before the visit", "2024-08-25T01:00:00+03:00"
    )
    assert value.precision == "approximate" and value.start < value.end
    assert value.reference.endswith("+03:00")
    assert narrative_time("three weeks ago", None).start is None
    assert narrative_time("February 31, 2024", "2024-08-25").start is None
    assert narrative_time("August 2", None).precision == "unknown"


def test_episode_delay_and_subject_controls():
    note, event = scenario("A")
    late = event.model_copy(deep=True)
    late.data["documented_at"] = "2024-08-22T10:00:00+02:00"
    a, b = extract_claims(note)[0], extract_claims(event)[0]
    assert compare_claims(a, b, late).status == "documentation_delay"
    assert (
        compare_claims(
            a.model_copy(update={"episode_id": "EP1"}),
            b.model_copy(update={"episode_id": "EP2"}),
            event,
        ).status
        == "different_episodes"
    )
    assert not structured_contradictions(
        [note], [record("Family history of headache.", "FAM", "clinical_event")]
    )
    foreign = record(NARRATIVES["A"][1], "FOREIGN", "clinical_event", patient_id="ANOTHER")
    assert not structured_contradictions([note], [foreign])


async def test_invalid_offsets_missing_evidence_and_model_proposals():
    note, event = scenario("A")
    candidate = structured_contradictions([note], [event])[0]
    verifier = EvidenceVerifier(Resolver([note, event]), "SYN-INDEPENDENT", "structured")
    for mutation in [
        {"char_start": 1},
        {"char_end": 100000},
        {"source_hash": "0" * 64},
        {"expected": "invented"},
    ]:
        invalid = candidate.model_copy(deep=True)
        invalid.anchors[0] = invalid.anchors[0].model_copy(update=mutation)
        assert (await verifier.verify(invalid))[0].status == "rejected"
    incomplete = candidate.model_copy(deep=True)
    incomplete.anchors = incomplete.anchors[:2]
    assert (await verifier.verify(incomplete))[0].status == "inconclusive"
    claim = extract_claims(note)[0]
    assert validate_model_claim(
        note, claim.model_copy(update={"extraction_method": "model_proposal"})
    )
    assert not validate_model_claim(note, claim.model_copy(update={"patient_id": "OTHER"}))
    assert not validate_model_claim(
        note,
        claim.model_copy(
            update={"time": claim.time.model_copy(update={"start": date(1999, 1, 1)})}
        ),
    )
    with pytest.raises(ValidationError):
        Anchor.model_validate({**claim.anchor.model_dump(), "char_end": None})


def test_unknown_followup_and_medication_order_not_use():
    referral = record(
        "",
        "REF",
        "referral",
        status="scheduled",
        ordered_at="2024-08-01T10:00:00Z",
        appointment_at="2024-09-01T10:00:00Z",
    )
    finding = followups([referral])[0]
    assert finding.rule == "interpretation"
    assert "does not establish completion" in finding.claim
    medication = record(
        "",
        "MED",
        "medication",
        status="ordered",
        medication_name="Synthetic medication",
        ordered_at="2024-08-01T10:00:00Z",
    )
    finding = medication_observations([medication])[0]
    assert "adherence" in finding.limitations[0]
    assert "causation" in finding.limitations[0]


def test_incompatible_analytes_and_units_not_compared():
    first = record(
        "",
        "L1",
        "observation",
        test_name="Analyte A",
        test_code="A",
        unit="mg/L",
        value_numeric=2,
        specimen_collected_at="2024-08-01T10:00:00Z",
    )
    other = record(
        "",
        "L2",
        "observation",
        test_name="Analyte A",
        test_code="B",
        unit="mg/L",
        value_numeric=8,
        specimen_collected_at="2024-08-02T10:00:00Z",
    )
    assert not lab_changes([first, other])
    other.data.update(test_code="A", unit="g/L")
    assert not lab_changes([first, other])


@pytest.mark.parametrize(
    "text",
    [
        "Cough first began on May 7, 2023; no cough before then.",
        "History: Cough first started on May 7, 2023.",
        "Patient first experienced coughing on May 7, 2023.",
    ],
)
def test_calendar_may_is_not_modal_uncertainty(text):
    claim = next(c for c in extract_claims(record(text)) if c.assertion == "onset")
    assert claim.certainty == "asserted"
    assert claim.time.start == date(2023, 5, 7)


def test_full_context_policy_selects_assertion_not_chief_concern():
    from app.clinical.rules import contradictions

    note = record("Headache first began on August 18, 2024; no headache before then.")
    earlier = record(
        "Chief concern: Headache. History: Headache present for ten days.",
        "EARLIER",
        event_at="2024-08-02T10:00:00+02:00",
        authored_at="2024-08-02T11:00:00+02:00",
    )
    event = record("Headache present.", "EVENT-B", "clinical_event")
    finding = contradictions([note, earlier], [event])[0]
    context = next(a for a in finding.anchors if a.source == earlier.source)
    # Contextual onset evidence must contain a substantive assertion.
    assert "Headache present for ten days" in context.quote


def test_timezone_day_boundary_and_unknown_episode():
    note = record("Headache first began on August 18, 2024.", event_at="2024-08-25T10:00:00+03:00")
    event = record(
        "Headache present.",
        "EV",
        "clinical_event",
        occurred_at="2024-08-17T23:30:00-03:00",
        documented_at="2024-08-17T23:45:00-03:00",
    )
    assert not structured_contradictions([note], [event])
    note, event = scenario("A")
    note = record("Headache started on August 18, 2024.")
    finding = structured_contradictions([note], [event])[0]
    assert finding.rule == "interpretation"


def test_clause_contrast_and_prior_absence_scope():
    claims = extract_claims(record("Denies fever but cough persists."))
    assert next(c for c in claims if c.concept == "cough").polarity == "positive"
    claim = extract_claims(record("No history of cough before this episode."))[0]
    assert claim.time.precision == "unknown" and claim.temporality == "historical"


def test_same_day_polarity_conflict_is_unresolved():
    note = record("Patient reports cough.")
    other = record("Patient denies cough.", "OPPOSING")
    finding = structured_contradictions([note, other], [])[0]
    assert finding.rule == "interpretation"


def test_hypothesis_evidence_is_not_positional():
    from app.agents.analysis import challenge

    note, event = scenario("A")
    finding = structured_contradictions([note], [event])[0]
    assessment = challenge([finding])[0]
    assert not assessment.supports  # No source explicitly supports separate episodes.
    assert assessment.weakens[0].source == note.source
    assert assessment.verdict == "inconclusive" and assessment.missing_evidence
    finding.anchors.reverse()
    assert challenge([finding])[0] == assessment


@pytest.mark.parametrize(
    "kind,status,passage,extra",
    [
        ("referral", "completed", "Referral LINK-1 was not completed.", {}),
        ("medication", "active", "LINK-1 was discontinued.", {}),
        (
            "observation",
            "final",
            "Result LINK-1 remains pending.",
            {"reported_at": "2024-08-01T10:00:00Z"},
        ),
    ],
)
async def test_linked_assertions_are_questions_not_verified_clinical_truth(
    kind, status, passage, extra
):
    from app.clinical.relationships import investigative_relationships

    note = record(passage)
    target = record("", "LINK-1", kind, status=status, **extra)
    finding = investigative_relationships([note, target])[0]
    result, _ = await EvidenceVerifier(
        Resolver([note, target]), "SYN-INDEPENDENT", "structured"
    ).verify(finding)
    assert result.status == "inconclusive"
    assert not investigative_relationships([record(passage.replace("LINK-1", "LINK-10")), target])


def test_recorded_states_and_units_are_preserved():
    lab = record(
        "",
        "LAB",
        "observation",
        test_name="Sodium",
        value_numeric=140,
        unit="mmol/L",
        specimen_collected_at="2024-08-01T10:00:00+03:00",
    )
    claim = extract_claims(lab)[0]
    assert claim.value == 140 and claim.unit == "mmol/L"
    assert claim.timestamps["specimen_collected_at"].endswith("+03:00")
    medication = record("", "MED", "medication", medication_name="Example", status="ordered")
    assert extract_claims(medication)[0].recorded_status == "ordered"


def test_unsupported_model_semantics_and_search_hit_rejected():
    note, _ = scenario("A")
    claim = extract_claims(note)[0]
    assert not validate_model_claim(note, claim.model_copy(update={"certainty": "hypothetical"}))
    hit = note.model_copy(update={"representation": "search_hit"})
    assert not extract_claims(hit)
    assert not anchor_matches(hit, claim.anchor)


def test_modifiers_and_headings_do_not_change_subject_or_episode():
    claim = extract_claims(record("Chief concern: Dry cough and intermittent heartburn."))[0]
    assert claim.episode_scope == "unspecified"
    assert claim.qualifiers == ["dry"]
    family = extract_claims(record("Family history: asthma."))[0]
    assert family.subject == "family" and family.section == "Family history"
    planned = extract_claims(record("Plan: Review persistent cough."))[0]
    assert planned.certainty == "hypothetical"


async def test_optional_model_interface_checks_every_proposed_claim():
    from app.llm.claims import ClaimProposals, validated_proposals

    note, _ = scenario("A")
    claim = extract_claims(note)[0]

    class FakeProvider:
        async def propose_claims(self, source):
            return ClaimProposals(
                claims=[claim, claim.model_copy(update={"patient_id": "FOREIGN"})]
            )

    accepted, rejected = await validated_proposals(FakeProvider(), note)
    assert len(accepted) == 1 and rejected == 1


def test_budgets_preserve_original_text_and_report_truncation():
    from app.clinical.reasoning import reasoning_limitations

    huge = record("Cough. " * 15000)
    assert not extract_claims(huge)
    assert reasoning_limitations([huge])
    assert reasoning_limitations([record("No symptoms.", f"N-{i}") for i in range(101)])


def test_decimal_statement_and_resolution_period_remain_intact():
    row = record("History: Cough present for 2.5 weeks. No fever.")
    claim = extract_claims(row)[0]
    assert claim.anchor.quote == "History: Cough present for 2.5 weeks."
    assert anchor_matches(row, claim.anchor)
    resolution = extract_claims(record("Cough resolved last month."))[0]
    assert resolution.assertion == "resolution"
    assert (resolution.time.start, resolution.time.end) == (date(2024, 7, 1), date(2024, 7, 31))
