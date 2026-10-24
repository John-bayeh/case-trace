"""Unfamiliar diagnostic workflows and independent search/counterevidence controls."""

import json
from pathlib import Path

import pytest
from test_clinical_relationships import Resolver
from test_hospital import migrate

from app.clinical.result_followup import result_relationships, search_scope
from app.composition import build_engine
from app.core.config import Settings
from app.core.database import Database
from app.core.provenance import digest
from app.evidence.verification import EvidenceVerifier
from app.hospital.adapter import SimulatedHospitalAdapter
from app.hospital.asset_service import LocalAssetReader
from app.hospital.assets import LocalAssetStorage
from app.hospital.ingestion import ingest
from app.hospital.validation import validate_case
from app.orchestration.store import InvestigationStore
from app.schemas.investigation import Candidate, CreateInvestigation, SourceRecord

PATIENT = "SYN-RELATIONSHIP"
EARLY = "2024-02-01T10:00:00+02:00"
LATER = "2024-03-01T10:00:00+02:00"


def row(kind, identifier, **data):
    data = {"id": identifier, "patient_id": PATIENT, **data}
    return SourceRecord(
        source={"type": kind, "id": identifier},
        source_version=1,
        source_hash=digest(data),
        data=data,
    )


def note(text, identifier="NOTE-A", when=LATER, kind="progress_note", **kwargs):
    return row(
        "document",
        identifier,
        text_content=text,
        event_at=when,
        authored_at=kwargs.pop("authored_at", when),
        document_type=kind,
        **kwargs,
    )


def workflow(extra=None):
    return [
        row(
            "diagnostic_report",
            "RESULT-X",
            status="final",
            issued_at=EARLY,
            title="Unfamiliar assay report",
            document_id="ORIGINAL-X",
            conclusion="Abnormal result requiring clinical follow-up.",
        ),
        note(
            "RESULT-X. Recommendation: specialist review and interval follow-up.",
            "ORIGINAL-X",
            EARLY,
        ),
        note(
            "RESULT-X. Result routed electronically; not acknowledged. "
            "Administrative queue closed. No patient communication documented.",
            "ROUTING-X",
        ),
        *(extra or []),
    ]


class Reader(Resolver):
    async def records(self, kind, patient_id, filters):
        rows = [r for (k, _), r in self.rows.items() if k == kind]
        return rows[: filters["limit"]], len(rows)

    async def search_documents(self, patient_id, query, filters):
        raise AssertionError("Verifier uses the independent unfiltered clinical reader")


async def verify(rows, candidate=None, originals=None):
    if candidate is None:
        (candidate,) = result_relationships(rows, search_scope(rows, True))
    return await EvidenceVerifier(Reader(originals or rows), PATIENT).verify(candidate)


def stage(candidate, name):
    return next(s for s in candidate.relationship.result_workflow.lifecycle if s.stage == name)


def proposal(rows):
    (candidate,) = result_relationships(rows, search_scope(rows, True))
    return candidate


async def test_unknown_outcome_and_routing_do_not_prove_acknowledgment_or_communication():
    rows = workflow()
    c = proposal(rows)
    verdict, claim = await verify(rows, c)
    assert verdict.status == "verified"
    assert stage(c, "routed").state == "documented"
    assert stage(c, "acknowledged").state == "unknown"
    assert stage(c, "patient_notification").state == "unknown"
    assert stage(c, "completed").state == "unknown"
    assert "does not prove non-occurrence" in claim
    assert "No completed follow-up is documented" in claim


async def test_proper_followup_preserves_completion_and_notification():
    rows = workflow([note("RESULT-X. Follow-up completed. Patient notified.", "DONE-X")])
    c = proposal(rows)
    verdict, claim = await verify(rows, c)
    assert verdict.status == "verified"
    assert stage(c, "completed").state == "documented"
    assert "No completed follow-up" not in claim
    assert "Later/current completed review" in claim
    assert "Patient notification is documented" in claim


async def test_scheduled_referral_is_not_completed():
    rows = workflow(
        [
            row(
                "referral",
                "REF-X",
                reason="RESULT-X follow-up",
                status="scheduled",
                ordered_at=EARLY,
                appointment_at=LATER,
            )
        ]
    )
    c = proposal(rows)
    assert stage(c, "scheduled").state == "documented"
    assert stage(c, "completed").state == "partial"
    assert (await verify(rows, c))[0].status == "verified"


async def test_completed_referral_is_later_counterevidence():
    rows = workflow(
        [
            row(
                "referral",
                "REF-X",
                reason="RESULT-X follow-up",
                status="completed",
                ordered_at=EARLY,
                appointment_at=LATER,
            )
        ]
    )
    assert "No completed follow-up" not in (await verify(rows))[1]


async def test_external_completion_is_unverified_and_explicitly_scoped():
    rows = workflow(
        [note("RESULT-X. Patient reports follow-up completed outside current records.")]
    )
    c = proposal(rows)
    # Patient-reported external care must not be promoted to verified completed care.
    assert stage(c, "completed").state != "documented"
    assert "Later/current completed review" not in c.claim
    assert (await verify(rows, c))[0].status == "verified"
    assert any("external" in s.lower() for s in c.limitations)


async def test_late_entry_does_not_date_care_by_authoring_time():
    rows = workflow(
        [
            note(
                "RESULT-X. Follow-up completed on 2024-02-09.",
                "LATE-X",
                authored_at="2024-06-01T10:00:00+02:00",
            )
        ]
    )
    c = proposal(rows)
    done = stage(c, "completed").observations[0]
    assert done.literal_dates == ["2024-02-09"]
    assert done.event_time_field is None
    assert done.timestamps["authored_at"].startswith("2024-06")
    assert "timing relative to the result remains uncertain" in (await verify(rows, c))[1]


async def test_duplicate_result_is_one_workflow():
    rows = workflow()
    duplicate = rows[0].model_copy(deep=True)
    duplicate.source.id = "RESULT-DUPLICATE"
    duplicate.data["id"] = duplicate.source.id
    duplicate.source_hash = digest(duplicate.data)
    rows.append(duplicate)
    assert len(result_relationships(rows, search_scope(rows, True))) == 1


@pytest.mark.parametrize("conclusion", ["Normal result.", "No abnormal result."])
def test_normal_result_without_actionable_recommendation(conclusion):
    rows = workflow()
    rows[0].data["conclusion"] = conclusion
    rows[1].data["text_content"] = "Normal result; no actionable recommendation."
    assert result_relationships(rows, search_scope(rows, True)) == []


async def test_unknown_outcome_does_not_become_negligence_from_candidate_prose():
    rows = workflow()
    c = proposal(rows)
    c.claim = "The clinician was negligent and the patient was never informed."
    verdict, claim = await verify(rows, c)
    assert verdict.status == "verified"
    assert "negligent" not in claim and "never informed" not in claim


@pytest.mark.parametrize("intent", ["causality", "diagnosis", "ingestion"])
async def test_unsupported_intents_rejected(intent):
    rows = workflow()
    c = proposal(rows)
    c.relationship.conclusion_kind = intent
    assert (await verify(rows, c))[0].status == "rejected"


async def test_omitted_later_completion_detected_by_independent_search():
    rows = workflow()
    c = proposal(rows)
    assert (await verify(rows, c, rows + [note("RESULT-X. Follow-up completed.", "HIDDEN-DONE")]))[
        0
    ].status == "rejected"


async def test_truncated_scope_cannot_verify_absence():
    rows = workflow()
    c = proposal(rows)
    c.relationship.result_workflow.search.complete = False
    assert (await verify(rows, c))[0].status == "inconclusive"


async def test_resolve_only_capability_cannot_verify_absence():
    rows = workflow()
    assert (await EvidenceVerifier(Resolver(rows), PATIENT).verify(proposal(rows)))[
        0
    ].status == "inconclusive"


@pytest.mark.parametrize("tamper", ["date", "recommendation", "stage", "source", "patient"])
async def test_source_and_lifecycle_tampering_rejected(tamper):
    rows = workflow()
    c = proposal(rows)
    if tamper == "stage":
        stage(c, "completed").state = "documented"
    elif tamper == "date":
        c.relationship.assertions[0].timestamps["issued_at"] = LATER
    elif tamper == "recommendation":
        c.relationship.assertions[1].value = "No follow-up recommended"
    elif tamper == "source":
        c.anchors[0].source_hash = "forged"
    else:
        rows[0].data["patient_id"] = "OTHER-PATIENT"
    assert (await verify(rows, c))[0].status == "rejected"


def test_ambiguous_multiple_results_do_not_share_generic_followup():
    rows = workflow()
    second = row(
        "diagnostic_report",
        "RESULT-Y",
        status="final",
        issued_at=EARLY,
        title="Another assay",
        document_id="ORIGINAL-Y",
        conclusion="Abnormal result.",
    )
    rows.extend([second, note("Recommendation: specialist review and follow-up.", "GENERIC")])
    c = proposal(rows)
    assert all(
        o.anchor.source.id != "GENERIC"
        for s in c.relationship.result_workflow.lifecycle
        for o in s.observations
    )


@pytest.mark.parametrize("text", ["", "Unparsed text. " * 200])
async def test_unreadable_or_over_limit_document_cannot_support_absence(text):
    rows = workflow([note(text, "UNPARSED")])
    assert (await verify(rows))[0].status == "inconclusive"


def test_negated_completion_is_not_completed_care():
    rows = workflow([note("RESULT-X. No documentation of completed specialist appointment.")])
    assert stage(proposal(rows), "completed").state == "partial"


def test_conflicting_closure_dates_remain_literal_and_conflicting():
    rows = workflow([note("RESULT-X. Queue closed on 2024-04-20.", "CLOSURE-X")])
    assert stage(proposal(rows), "administrative_closure").state == "conflicting"


def test_discussion_with_colleague_is_not_patient_notification():
    rows = workflow([note("RESULT-X. Discussed result with laboratory colleague.")])
    assert stage(proposal(rows), "patient_notification").state == "unknown"


def test_originating_procedure_links_to_unique_earlier_order():
    rows = workflow(
        [
            note(
                "RESULT-X. Tissue sample obtained.",
                "PROC",
                kind="procedure_note",
                title="Peripheral tissue sampling procedure note",
            ),
            note(
                "Indication documented.",
                "ORDER",
                when=EARLY,
                kind="procedure_order",
                title="Peripheral tissue sampling order",
            ),
        ]
    )
    assert stage(proposal(rows), "ordered").observations[0].anchor.source.id == "ORDER"


async def test_different_snapshot_version_fails_closed():
    rows = workflow()
    c = proposal(rows)
    rows[-1].source_version = 2
    assert (await verify(rows, c))[0].status == "rejected"


async def test_missing_result_date_is_unknown_not_a_dated_completion_claim():
    rows = workflow([note("RESULT-X. Follow-up completed.", "DONE")])
    rows[0].data["issued_at"] = None
    rows[0].source_hash = digest(rows[0].data)
    c = proposal(rows)
    assert "timing relative to the result remains uncertain" in (await verify(rows, c))[1]


@pytest.mark.parametrize(
    "text",
    [
        "RESULT-X. If follow-up completed, review the note.",
        "RESULT-X. Follow-up not completed.",
        "RESULT-X. No documentation of completed specialist review or appointment.",
    ],
)
def test_conditional_and_negative_completion(text):
    assert not any(
        o.state == "documented"
        for o in stage(proposal(workflow([note(text)])), "completed").observations
    )


@pytest.mark.parametrize("strategy", ["baseline", "adaptive_rules"])
async def test_case003_real_tools_persisted_workflow_and_independent_verification(
    tmp_path, strategy
):
    root = Path(__file__).resolve().parents[3]
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'result.db'}",
        asset_storage_path=root / "data/assets",
        investigation_strategy=strategy,
    )
    migrate(settings)
    database = Database(settings)
    await database.initialize()
    try:
        validated = validate_case(
            root / "data/cases/CASE-003/case.json", LocalAssetStorage(settings.resolved_asset_path)
        )
        async with database.session() as session:
            await ingest(session, validated)
        store = InvestigationStore(database)
        identifier, _ = await store.create(CreateInvestigation(patient_id="SYN-003"), None)
        await build_engine(store, settings).execute(identifier)
        report = await store.report(identifier)
        assert report.status == "completed", report.limitations
        relationships = [
            f
            for f in report.verified_findings
            if f.relationship and f.relationship.relationship_type == "result_followup"
        ]
        (finding,) = relationships
        # Only the finalized report is compared with evaluator-only expectations.
        key = json.loads((root / "evaluation/CASE-003/answer-key.json").read_text())
        required = {s for f in key["expected_findings"] for s in f["required_source_ids"]}
        assert required <= {a.source.id for a in finding.anchors}
        assert "Later/current completed review" in finding.claim
        assert stage(finding, "administrative_closure").state == "conflicting"
        assert stage(finding, "ordered").state == "documented"
        assert len(finding.relationship.result_workflow.search.sources) == 27
        assert any("standalone appointments" in s for s in finding.limitations)
        tools = await store.queries.tools(identifier, 1000, 0)
        original_ids = {
            s.id
            for t in tools.items
            if t.tool == "get_document" and t.status == "succeeded"
            for s in t.source_refs
        }
        assert required <= original_ids
        assert all(t.status == "succeeded" for t in tools.items)
        clinical = SimulatedHospitalAdapter(
            database, LocalAssetReader(settings.resolved_asset_path)
        )
        candidate = Candidate.model_validate(
            {k: getattr(finding, k) for k in Candidate.model_fields}
        )
        verdict, claim = await EvidenceVerifier(clinical, "SYN-003").verify(candidate)
        assert verdict.status == "verified" and claim == finding.claim
        events = await store.events(identifier, 0, 1000)
        assert any(e.type == "relationship.verification_completed" for e in events)
    finally:
        await database.dispose()
