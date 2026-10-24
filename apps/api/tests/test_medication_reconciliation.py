"""Independent unfamiliar medication controls, never derived from evaluation keys."""

import pytest
from test_clinical_relationships import Resolver

from app.clinical.medication_identity import medication_identity
from app.clinical.medications import (
    laboratory_questions,
    medication_assertions,
    medication_relationships,
)
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.schemas import Medication
from app.schemas.investigation import SourceRecord


def order(
    status="discontinued",
    when="2024-02-01T10:00:00+02:00",
    identifier="ORDER-A",
    product="Controlol 10 mg tablet",
    ingredient="controlol",
    encounter="VISIT-A",
    start=None,
):
    data = Medication(
        id=identifier,
        patient_id="SYN-RELATIONSHIP",
        encounter_id=encounter,
        medication_name=product,
        generic_name=ingredient,
        route="oral",
        dose=10,
        dose_unit="mg",
        status=status,
        ordered_at=when,
        start_at=start,
    ).model_dump(mode="json")
    return SourceRecord(
        source={"type": "medication", "id": identifier},
        source_version=1,
        source_hash=digest(data),
        data=data,
    )


def note(
    text, when="2024-03-01T10:00:00+02:00", identifier="NOTE-B", encounter="VISIT-B", authored=None
):
    data = {
        "id": identifier,
        "patient_id": "SYN-RELATIONSHIP",
        "encounter_id": encounter,
        "text_content": text,
        "event_at": when,
        "authored_at": authored or when,
    }
    return SourceRecord(
        source={"type": "document", "id": identifier},
        source_version=1,
        source_hash=digest(data),
        data=data,
    )


async def verified(rows):
    candidates = medication_relationships(rows)
    for candidate in candidates:
        result, canonical = await EvidenceVerifier(Resolver(rows), "SYN-RELATIONSHIP").verify(
            candidate
        )
        assert result.status == "verified", result
        assert canonical == candidate.claim
    return candidates


@pytest.mark.parametrize(
    "text",
    [
        "Patient reports taking controlol but cannot confirm the last dose.",
        "External medication list includes controlol 10 mg daily marked active.",
        "Restart controlol tomorrow. Actual exposure remains uncertain.",
        "Patient cannot confirm the last dose of controlol.",
    ],
)
async def test_reconciliation_from_unfamiliar_records(text):
    rows = [order(), note(text)]
    candidates = await verified(rows)
    assert candidates
    assert len({a.source.id for a in candidates[0].anchors}) >= 2
    assert "unestablished" in candidates[0].claim


async def test_consistent_history_does_not_create_discrepancy():
    assert (
        medication_relationships([order("active"), note("Patient reports taking controlol daily.")])
        == []
    )


async def test_temporary_hold_followed_by_restart_is_not_called_conflict():
    candidates = await verified([order("held"), note("Restart controlol today.")])
    assert candidates and "hold followed by restart" in candidates[0].title
    assert "conflict" not in candidates[0].claim.casefold()


async def test_explicit_overlapping_planned_dates_are_consolidated():
    rows = [
        order("held"),
        note("Hold controlol until 2024-03-04.", "2024-03-01T10:00:00+02:00", "HOLD-NOTE"),
        note("Restart controlol on 2024-03-03.", "2024-03-02T10:00:00+02:00", "RESTART-NOTE"),
    ]
    candidates = await verified(rows)
    assert candidates and "Overlapping recorded" in candidates[0].title
    assert {"HOLD-NOTE", "RESTART-NOTE"} <= {a.source.id for a in candidates[0].anchors}


async def test_missing_ingredient_context_cannot_be_invented_from_generic_history():
    rows = [order("active"), note("Patient says the other medicine may have been taken.")]
    assert medication_relationships(rows) == []


async def test_conflicting_stop_restart_text_preserves_uncertainty():
    rows = [
        order("active"),
        note(
            "Medication list says controlol resumed tonight, "
            "but service instructions say continue holding until tomorrow."
        ),
        note(
            "Patient cannot confirm the last dose of controlol.",
            "2024-04-01T10:00:00+02:00",
            "NOTE-C",
        ),
    ]
    candidates = await verified(rows)
    assert candidates and "Conflicting recorded" in candidates[0].title


def test_different_formulations_are_not_merged_by_name():
    rows = [
        order(),
        order("active", identifier="ORDER-B", product="Controlol 10 mg extended-release capsule"),
        note("Patient reports taking controlol."),
    ]
    assert medication_identity(rows[0].data) != medication_identity(rows[1].data)
    assert medication_relationships(rows) == []


async def test_copied_active_list_never_verifies_ingestion():
    candidate = (
        await verified(
            [
                order(),
                note(
                    "Copied medication list includes controlol marked active. "
                    "This is not proof of administration."
                ),
            ]
        )
    )[0]
    assert any(a.origin == "copied_list" for a in candidate.relationship.assertions)
    assert not any(
        a.value == "administration_documented" for a in candidate.relationship.assertions
    )
    candidate.relationship.conclusion_kind = "ingestion"
    rows = [
        order(),
        note(
            "Copied medication list includes controlol marked active. "
            "This is not proof of administration."
        ),
    ]
    assert (await EvidenceVerifier(Resolver(rows), "SYN-RELATIONSHIP").verify(candidate))[
        0
    ].status == "rejected"


async def test_retrospective_order_time_is_not_intended_start():
    rows = [
        order(when="2024-03-01T10:00:00+02:00", start="2024-01-01"),
        note("Patient cannot confirm the last dose of controlol.", "2024-04-01T10:00:00+02:00"),
    ]
    candidate = (await verified(rows))[0]
    assertion = candidate.relationship.assertions[0]
    assert assertion.time.reference == rows[0].data["ordered_at"]
    assert assertion.timestamps["start_at"] == "2024-01-01"


async def test_incomplete_history_is_a_supported_documentation_finding():
    candidates = await verified(
        [order("active"), note("Patient cannot confirm the last dose of controlol.")]
    )
    assert candidates and "uncertainty" in candidates[0].title


def test_actions_do_not_transfer_between_drugs_or_negation():
    rows = [
        order(),
        order("active", identifier="ORDER-B", product="Otherol 10 mg tablet", ingredient="otherol"),
        note("Controlol is discontinued and otherol is ordered."),
    ]
    claims = medication_assertions(rows[-1], rows)
    assert not any("otherol" in a.concept and a.value == "discontinued" for a in claims)
    assert not any(
        a.value == "held" for a in medication_assertions(note("Do not hold controlol."), [order()])
    )
    assert not medication_assertions(
        note("Family history: mother reports taking controlol."), [order()]
    )
    assert not any(
        a.value == "held"
        for a in medication_assertions(note("If nausea develops, hold controlol."), [order()])
    )


@pytest.mark.parametrize("attack", ["version", "patient", "value", "missing"])
async def test_independent_verification_rejects_tampering(attack):
    rows = [order(), note("Patient reports taking controlol daily.")]
    candidate = medication_relationships(rows)[0]
    if attack == "version":
        rows[0].source_version = 2
    elif attack == "patient":
        rows[1].data["patient_id"] = "FOREIGN"
    elif attack == "value":
        candidate.relationship.assertions[0].value = "active"
    else:
        candidate.anchors = candidate.anchors[1:]
    assert (await EvidenceVerifier(Resolver(rows), "SYN-RELATIONSHIP").verify(candidate))[
        0
    ].status == "rejected"


async def test_causality_and_diagnosis_cannot_be_promoted():
    rows = [order(), note("Patient reports taking controlol daily.")]
    for intent in ["causality", "diagnosis"]:
        candidate = medication_relationships(rows)[0]
        candidate.relationship.conclusion_kind = intent
        assert (await EvidenceVerifier(Resolver(rows), "SYN-RELATIONSHIP").verify(candidate))[
            0
        ].status == "rejected"


async def test_lab_handoff_remains_a_question_and_preserves_evidence():
    from app.agents.analysis import lab_changes

    medication_rows = [order(), note("Patient reports taking controlol daily.")]
    medication = medication_relationships(medication_rows)[0]
    laboratories = []
    for day, value in [(10, 1.1), (15, 2.1)]:
        data = {
            "id": f"LAB-CONTEXT-{day}",
            "patient_id": "SYN-RELATIONSHIP",
            "test_name": "Creatinine",
            "test_code": "CREA",
            "unit": "mg/dL",
            "status": "final",
            "value_numeric": value,
            "reference_range_low": 0.5,
            "reference_range_high": 1.3,
            "specimen_collected_at": f"2024-02-{day}T10:00:00+02:00",
        }
        laboratories.append(
            SourceRecord(
                source={"type": "observation", "id": data["id"]},
                source_version=1,
                source_hash=digest(data),
                data=data,
            )
        )
    (lab,) = lab_changes(laboratories)
    verifier = EvidenceVerifier(Resolver(medication_rows + laboratories), "SYN-RELATIONSHIP")
    assert (await verifier.verify(lab))[0].status == "verified"
    questions = laboratory_questions([medication], [lab])
    assert len(questions) == 1 and questions[0].rule == "interpretation"
    assert "causality require review" in questions[0].claim
    assert (await verifier.verify(questions[0]))[0].status == "inconclusive"
