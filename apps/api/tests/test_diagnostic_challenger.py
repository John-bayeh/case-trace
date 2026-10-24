"""Independent hypothesis comparison controls; no evaluator data drives extraction."""

import json
from pathlib import Path

import pytest
from test_hospital import migrate
from test_result_followup import EARLY, LATER, PATIENT, Reader, note, row

from app.clinical.diagnostic_challenger import diagnostic_comparisons, working_assessment
from app.clinical.result_followup import search_scope
from app.composition import build_engine
from app.core.config import Settings
from app.core.database import Database
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import ingest
from app.hospital.validation import validate_case
from app.orchestration.store import InvestigationStore
from app.schemas.investigation import Candidate, CreateInvestigation

POSITIVE = (
    "Ambulatory monitor captured an arrhythmia with patient-triggered palpitations. "
    "The finding requires clinical interpretation."
)


def records(text=POSITIVE):
    return [
        note(
            "Working diagnosis: anxiety with recurrent palpitations.",
            "ASSESSMENT",
            EARLY,
            encounter_id="VISIT-A",
        ),
        note(text, "OBJECTIVE", LATER, kind="diagnostic_report", encounter_id="VISIT-B"),
    ]


def propose(rows):
    (candidate,) = diagnostic_comparisons(rows, search_scope(rows, True))
    return candidate


def comparison(candidate):
    return candidate.relationship.diagnostic_comparison


async def check(rows, candidate=None, originals=None):
    c = candidate or propose(rows)
    return await EvidenceVerifier(Reader(originals or rows), PATIENT).verify(c)


async def test_relevant_rhythm_finding_yields_a_provisional_question():
    rows = records()
    c = propose(rows)
    result, claim = await check(rows, c)
    assert result.status == "verified"
    assert comparison(c).provisional_verdict == "reconsideration_question"
    assert comparison(c).weakening_evidence[0].source.id == "OBJECTIVE"
    assert "Does anxiety fully explain" in claim
    assert "does not exclude" in claim


def test_anxiety_without_objective_result_does_not_generate_challenge():
    rows = records()[:1]
    assert diagnostic_comparisons(rows, search_scope(rows, True)) == []


@pytest.mark.parametrize(
    "text,verdict",
    [
        ("Monitor showed no arrhythmia during symptoms of palpitations.", "not_challenged"),
        (
            "Monitor captured an arrhythmia; incidental finding unrelated to symptoms.",
            "not_challenged",
        ),
        (
            "Monitor captured an arrhythmia with patient-triggered palpitations, "
            "possible artifact.",
            "inconclusive",
        ),
        ("Monitor inconclusive during palpitations.", "inconclusive"),
        ("Monitor result supports anxiety during symptoms of palpitations.", "not_challenged"),
        ("Monitor captured an arrhythmia with patient-triggered cough.", "not_challenged"),
    ],
)
async def test_negative_and_ambiguous_controls_do_not_become_challenges(text, verdict):
    rows = records(text)
    c = propose(rows)
    assert comparison(c).provisional_verdict == verdict
    assert (await check(rows, c))[0].status == "verified"


async def test_supportive_interpretation_retains_supporting_evidence():
    rows = records("Monitor result is consistent with anxiety during symptoms of palpitations.")
    assert comparison(propose(rows)).supporting_evidence
    assert not comparison(propose(rows)).weakening_evidence


async def test_wrong_result_document_encounter_is_inconclusive():
    rows = records() + [
        row(
            "diagnostic_report",
            "REPORT",
            document_id="OBJECTIVE",
            encounter_id="UNRELATED",
            status="final",
        )
    ]
    c = propose(rows)
    assert comparison(c).provisional_verdict == "inconclusive"
    assert any("encounter" in s for s in comparison(c).missing_evidence)
    assert (await check(rows, c))[0].status == "verified"


async def test_conflicting_interpretations_are_retained_not_selectively_ignored():
    rows = records() + [
        note(
            "Monitor showed no arrhythmia during symptoms of palpitations.",
            "COUNTER",
            LATER,
            kind="diagnostic_report",
            encounter_id="VISIT-B",
        )
    ]
    c = propose(rows)
    assert comparison(c).provisional_verdict == "inconclusive"
    assert comparison(c).contradictory_evidence[0].source.id == "COUNTER"
    assert (await check(rows, c))[0].status == "verified"


async def test_omitted_counterinterpretation_is_independently_discovered():
    rows = records()
    extra = note(
        "Monitor showed no arrhythmia during symptoms of palpitations.",
        "COUNTER",
        LATER,
        kind="diagnostic_report",
        encounter_id="VISIT-B",
    )
    assert (await check(rows, propose(rows), rows + [extra]))[0].status == "rejected"


def test_multiple_plausible_explanations_stay_provisional():
    c = propose(records())
    assert len(comparison(c).alternatives) >= 2
    assert comparison(c).missing_evidence
    assert "coexist" in comparison(c).alternatives[0]


def test_unfamiliar_working_label_and_explicit_certainty():
    rows = records()
    rows[0] = note(
        "Provisional diagnosis: stress response with recurrent palpitations.", "ASSESSMENT", EARLY
    )
    c = propose(rows)
    assert comparison(c).hypothesis == "stress response"
    assert comparison(c).certainty == "provisional"


def test_working_diagnosis_is_not_inferred_from_a_generic_template():
    assert (
        working_assessment(note("The working explanation is recorded, with routine follow-up."))
        is None
    )


@pytest.mark.parametrize(
    "tamper", ["patient", "hash", "date", "verdict", "certainty", "source_role", "missing_anchor"]
)
async def test_independent_reconstruction_rejects_tampering(tamper):
    rows = records()
    c = propose(rows)
    if tamper == "patient":
        rows[0].data["patient_id"] = "FOREIGN"
    elif tamper == "hash":
        c.anchors[0].source_hash = "forged"
    elif tamper == "date":
        comparison(c).evidence[0].timestamps["event_at"] = LATER
    elif tamper == "verdict":
        comparison(c).provisional_verdict = "not_challenged"
    elif tamper == "certainty":
        comparison(c).certainty = "provisional"
    elif tamper == "source_role":
        comparison(c).evidence[0].role = "objective_interpretation"
    else:
        c.anchors.pop()
    assert (await check(rows, c))[0].status == "rejected"


@pytest.mark.parametrize("intent", ["diagnosis", "causality", "ingestion"])
async def test_definitive_or_causal_intents_fail(intent):
    rows = records()
    c = propose(rows)
    c.relationship.conclusion_kind = intent
    assert (await check(rows, c))[0].status == "rejected"


async def test_candidate_prose_does_not_publish_diagnosis_probability_or_treatment():
    rows = records()
    c = propose(rows)
    c.claim = (
        "Anxiety is absent. The patient definitely has a rhythm diagnosis, "
        "probability 99%. Start treatment."
    )
    verdict, claim = await check(rows, c)
    assert verdict.status == "verified"
    assert (
        "99%" not in claim and "Start treatment" not in claim and "Anxiety is absent" not in claim
    )


@pytest.mark.parametrize("text", ["", "Unparsed. " * 250])
async def test_unparsed_counterevidence_cannot_be_silently_excluded(text):
    rows = records() + [note(text, "UNKNOWN")]
    assert (await check(rows))[0].status == "inconclusive"


async def test_unknown_chronology_is_not_replaced_by_authored_time():
    rows = records()
    rows[1].data["event_at"] = None
    rows[1].source_hash = digest(rows[1].data)
    assert comparison(propose(rows)).provisional_verdict == "inconclusive"


@pytest.mark.parametrize("strategy", ["baseline", "adaptive_rules"])
async def test_case004_real_tools_source_comparison_and_persistence(tmp_path, strategy):
    root = Path(__file__).resolve().parents[3]
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'hypothesis.db'}",
        asset_storage_path=root / "data/assets",
        investigation_strategy=strategy,
    )
    migrate(settings)
    database = Database(settings)
    await database.initialize()
    try:
        validated = validate_case(
            root / "data/cases/CASE-004/case.json", LocalAssetStorage(settings.resolved_asset_path)
        )
        async with database.session() as session:
            await ingest(session, validated)
        store = InvestigationStore(database)
        identifier, _ = await store.create(CreateInvestigation(patient_id="SYN-004"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        assert report.status == "completed", report.limitations
        comparisons = [
            f
            for f in report.verified_findings
            if f.relationship and f.relationship.diagnostic_comparison
        ]
        (finding,) = comparisons
        assert comparison(finding).provisional_verdict == "reconsideration_question"
        assert any(h.comparison and h.verdict == "inconclusive" for h in report.hypotheses)
        key = json.loads((root / "evaluation/CASE-004/answer-key.json").read_text())
        required = {s for f in key["expected_findings"] for s in f["required_source_ids"]}
        assert required <= {a.source.id for a in finding.anchors}
        tools = await store.queries.tools(identifier, 1000, 0)
        retrieved = {
            s.id
            for t in tools.items
            if t.tool == "get_document" and t.status == "succeeded"
            for s in t.source_refs
        }
        assert required <= retrieved
        assert all(t.status == "succeeded" for t in tools.items)
        # Report roundtrip retains the typed comparison and source versions.
        assert Candidate.model_validate(
            finding.model_dump(
                exclude={
                    "id",
                    "investigation_id",
                    "status",
                    "support_level",
                    "verification",
                    "created_at",
                    "verified_at",
                }
            )
        ).relationship.diagnostic_comparison == comparison(finding)
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "text",
    [
        "No working diagnosis: anxiety with palpitations.",
        "Family history: mother's initial assessment documents anxiety and palpitations.",
        "Working diagnosis: no anxiety with palpitations.",
    ],
)
def test_negated_or_family_assessment_is_not_the_patient_working_diagnosis(text):
    assert working_assessment(note(text)) is None


def test_separate_symptom_note_in_same_encounter_is_retained():
    rows = records()
    rows[0] = note("Working diagnosis: anxiety.", "ASSESSMENT", EARLY, encounter_id="VISIT-A")
    rows.append(note("Recurrent palpitations reported.", "SYMPTOM", EARLY, encounter_id="VISIT-A"))
    c = propose(rows)
    assert comparison(c).provisional_verdict == "reconsideration_question"
    assert any(e.role == "symptom_context" for e in comparison(c).evidence)


def test_unrelated_encounter_symptoms_do_not_supply_missing_working_context():
    rows = records()
    rows[0] = note("Working diagnosis: anxiety.", "ASSESSMENT", EARLY, encounter_id="VISIT-A")
    rows.append(note("Palpitations reported.", "SYMPTOM", EARLY, encounter_id="UNRELATED"))
    assert diagnostic_comparisons(rows, search_scope(rows, True)) == []


def test_negated_symptoms_do_not_support_positive_correlation():
    rows = records()
    rows[0] = note("Working diagnosis: anxiety with no palpitations.", "ASSESSMENT", EARLY)
    assert diagnostic_comparisons(rows, search_scope(rows, True)) == []


def test_relative_test_does_not_become_patient_objective_finding():
    rows = records("Mother's monitor captured an arrhythmia with patient-triggered palpitations.")
    assert comparison(propose(rows)).provisional_verdict == "inconclusive"


def test_different_test_modalities_are_not_conflicting_interpretations():
    rows = records() + [
        note(
            "ECG showed no arrhythmia during symptoms of palpitations.",
            "ECG-OTHER",
            LATER,
            kind="diagnostic_report",
            encounter_id="VISIT-B",
        )
    ]
    assert not comparison(propose(rows)).contradictory_evidence


async def test_incomplete_search_cannot_verify_a_comparison():
    rows = records()
    c = propose(rows)
    comparison(c).search.complete = False
    assert (await check(rows, c))[0].status == "inconclusive"
