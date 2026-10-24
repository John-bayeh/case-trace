"""Independent controls for an offline evaluator; no agent execution or clinical edits."""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from clinical_discovery import (  # noqa: E402
    DIMENSIONS,
    Judgment,
    Specification,
    assess,
    evaluate,
    sha,
)

from app.core.provenance import digest  # noqa: E402
from app.schemas.investigation import SourceRecord  # noqa: E402

CONTROLS = json.loads(
    (Path(__file__).parent / "fixtures/clinical-discovery-controls.json").read_text()
)["controls"]


def fixture(control):
    sources = {}
    anchors = []
    for name in ["A", "B"]:
        data = {
            "id": name,
            "patient_id": "CONTROL-PATIENT",
            "encounter_id": "CONTROL-VISIT",
            "text_content": f"Independent synthetic record {name}",
        }
        if control.get("foreign") == name:
            data["patient_id"] = "OTHER-PATIENT"
        sources[name] = SourceRecord(
            source={"id": name, "type": "document"},
            source_version=1,
            source_hash=digest(data),
            data=data,
        )
        if control.get("omit") != name:
            anchors.append(
                {
                    "source": {"id": name, "type": "document"},
                    "source_version": 1,
                    "source_hash": digest(data),
                    "encounter_id": "CONTROL-VISIT",
                    "field": "text_content",
                    "expected": data["text_content"],
                }
            )
    roles = {"order": ["A"], "report": ["B"]}
    spec = Specification(
        version="1.0",
        case_id="CONTROL",
        dataset_version="1",
        key_sha256="unused-in-pure-core",
        discoveries=[
            {
                "finding_key": "discovery",
                "domain": "medication_reconciliation_discrepancy",
                "priority": "primary",
                "source_roles": roles,
                "review_required": ["Qualified semantic review"],
            }
        ],
    )
    key = {
        "case_id": "CONTROL",
        "dataset_version": "1",
        "expected_findings": [
            {
                "finding_key": "discovery",
                "required_source_ids": ["A", "B"],
                "acceptable_outcomes": ["verified", "unresolved"],
                "expected_claim": "Reconcile order and report without asserting ingestion.",
            }
        ],
    }
    finding = {
        "id": "F1",
        "claim": control["claim"],
        "claim_kind": "interpretation",
        "status": "unresolved",
        "anchors": anchors,
    }
    report = {"status": "completed", "verified_findings": [], "unresolved_findings": [finding]}
    if control.get("split"):
        report["unresolved_findings"] = [
            {**finding, "id": f"F{i}", "anchors": [a]} for i, a in enumerate(anchors)
        ]
    decisions = {d: "pass" for d in DIMENSIONS}
    if control["decision"] not in {"pass", "none"}:
        decisions[control["decision"]] = "fail"
    review = Judgment(
        finding_key="discovery",
        finding_ids=["F1"],
        linked_relationship=control["claim"],
        source_roles=roles,
        decisions=decisions,
        rationale={d: f"Independent authored control: {d} is {decisions[d]}" for d in DIMENSIONS},
    )
    return report, key, spec, sources, [] if control["decision"] == "none" else [review]


@pytest.mark.parametrize("control", CONTROLS, ids=[c["name"] for c in CONTROLS])
def test_independent_controls(control):
    report, key, spec, sources, reviews = fixture(control)
    result = assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)
    assert result["discoveries"][0]["outcome"] == control["outcome"]
    # Without qualified adjudication, even positive control text cannot pass.
    assert not assess(report, key, spec, sources, "CONTROL-PATIENT")["primary_discovery_success"]


def test_full_coverage_and_no_relationship_is_not_success():
    report, key, spec, sources, _ = fixture(CONTROLS[0])
    result = assess(report, key, spec, sources, "CONTROL-PATIENT")
    row = result["discoveries"][0]
    assert row["verified_citation_sources"] == ["A", "B"]
    assert row["outcome"] == "not_assessable"
    assert row["source_retrieval"] is None


def test_explicit_linked_group_requires_reviewed_relationship():
    report, key, spec, sources, _ = fixture(
        next(c for c in CONTROLS if c["name"] == "disconnected_union")
    )
    _, _, _, _, reviews = fixture(CONTROLS[0])
    reviews[0].finding_ids = ["F0", "F1"]
    report["unresolved_findings"][0]["claim"] = (
        "The order in this finding differs from reported use in F1; actual exposure is unknown."
    )
    reviews[0].linked_relationship = report["unresolved_findings"][0]["claim"]
    reviews[0].link_claim_finding_id = "F0"
    result = assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)
    assert result["primary_discovery_success"]


def test_reviewer_cannot_invent_link_between_unrelated_findings():
    report, key, spec, sources, _ = fixture(
        next(c for c in CONTROLS if c["name"] == "disconnected_union")
    )
    _, _, _, _, reviews = fixture(CONTROLS[0])
    reviews[0].finding_ids = ["F0", "F1"]
    with pytest.raises(ValueError, match="original finding claim"):
        assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)


@pytest.mark.parametrize(
    "mutation", ["hash", "version", "field", "value", "type", "encounter", "quote", "span"]
)
def test_anchor_tampering_fails_closed(mutation):
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    anchor = report["unresolved_findings"][0]["anchors"][0]
    if mutation == "hash":
        anchor["source_hash"] = "0" * 64
    elif mutation == "version":
        anchor["source_version"] = 2
    elif mutation == "field":
        anchor["field"] = "missing"
    elif mutation == "value":
        anchor["expected"] = "fabricated"
    elif mutation == "type":
        anchor["source"]["type"] = "observation"
    elif mutation == "encounter":
        anchor["encounter_id"] = "OTHER-VISIT"
    elif mutation == "quote":
        anchor["quote"] = "fabricated"
    else:
        anchor.update(quote="Independent", char_start=1, char_end=12)
    assert (
        assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)["discoveries"][0]["outcome"]
        == "unsupported"
    )


def test_no_findings_is_missed():
    report, key, spec, sources, _ = fixture(CONTROLS[0])
    report["unresolved_findings"] = []
    assert (
        assess(report, key, spec, sources, "CONTROL-PATIENT")["discoveries"][0]["outcome"]
        == "missed"
    )


def test_unresolved_must_be_accepted_by_key():
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    key["expected_findings"][0]["acceptable_outcomes"] = ["verified"]
    assert (
        assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)["discoveries"][0]["outcome"]
        == "partial"
    )


def test_provisional_roles_block_exact():
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    spec.discoveries[0].source_roles = {"pending_role_review": ["A", "B"]}
    reviews[0].source_roles = spec.discoveries[0].source_roles
    assert (
        assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)["discoveries"][0]["outcome"]
        == "not_assessable"
    )


def test_incomplete_semantic_review_is_rejected():
    _, _, _, _, reviews = fixture(CONTROLS[0])
    data = reviews[0].model_dump()
    del data["decisions"]["causality"]
    with pytest.raises(ValueError):
        Judgment.model_validate(data)


@pytest.mark.parametrize("phase", ["before", "after"])
@pytest.mark.parametrize("number", range(1, 7))
def test_frozen_baseline_reproduces(phase, number):
    case = f"CASE-{number:03}"
    source = ROOT / f"docs/evaluation/artifacts/generalization/{phase}/{case}"
    measured = json.loads(
        (ROOT / f"docs/evaluation/artifacts/phase2-01/{phase}/{case}.json").read_text()
    )
    assert (
        evaluate(
            source / "report.json",
            ROOT / f"evaluation/{case}/answer-key.json",
            ROOT / f"evaluation/clinical-discovery/v1/{case}.json",
            ROOT / f"data/cases/{case}/case.json",
            tools_path=source / "tools.json",
        )
        == measured["multi_domain"]
    )


def test_review_cannot_be_replayed_after_report_changes(tmp_path):
    case = "CASE-001"
    report = ROOT / f"docs/evaluation/artifacts/generalization/after/{case}/report.json"
    spec = ROOT / f"evaluation/clinical-discovery/v1/{case}.json"
    canonical = ROOT / f"data/cases/{case}/case.json"
    review = {
        "version": "1.0",
        "report_sha256": sha(report),
        "spec_sha256": sha(spec),
        "case_sha256": sha(canonical),
        "reviewer": "Protocol test",
        "qualification": "Authored test oracle",
        "reviewed_at": "2026-10-22",
        "judgments": [],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review))
    modified = tmp_path / "report.json"
    data = json.loads(report.read_text())
    data["summary"] = copy.copy(data["summary"])
    data["summary"]["test"] = "Changed report bytes"
    modified.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Stale"):
        evaluate(modified, ROOT / f"evaluation/{case}/answer-key.json", spec, canonical, path)


def test_frozen_inventory_remains_unchanged():
    inventory = json.loads(
        (ROOT / "docs/evaluation/artifacts/phase2-01/frozen-hashes.json").read_text()
    )
    for name, expected in inventory.items():
        assert sha(ROOT / name) == expected, name


def test_key_anchor_required_inside_selected_group():
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    key["expected_findings"][0]["anchors"] = [
        {"source_id": "A", "field": "text_content", "quote": "Decisive passage absent"}
    ]
    row = assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)["discoveries"][0]
    assert row["outcome"] != "exact"
    assert not row["groups"][0]["key_anchors_matched"]


def test_semantic_review_decision_stays_unassessed():
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    reviews[0].decisions["causality"] = "review"
    assert (
        assess(report, key, spec, sources, "CONTROL-PATIENT", reviews)["discoveries"][0]["outcome"]
        == "not_assessable"
    )


def test_no_report_supplied_approval_is_trusted():
    report, key, spec, sources, reviews = fixture(CONTROLS[0])
    report["review"] = reviews[0].model_dump()
    assert not assess(report, key, spec, sources, "CONTROL-PATIENT")["primary_discovery_success"]


@pytest.mark.parametrize("binding", ["report_sha256", "spec_sha256", "case_sha256"])
def test_review_bindings_and_key_binding(tmp_path, binding):
    source = ROOT / "docs/evaluation/artifacts/generalization/after/CASE-001/report.json"
    spec = ROOT / "evaluation/clinical-discovery/v1/CASE-001.json"
    case = ROOT / "data/cases/CASE-001/case.json"
    key = ROOT / "evaluation/CASE-001/answer-key.json"
    review = {
        "version": "1.0",
        "report_sha256": sha(source),
        "spec_sha256": sha(spec),
        "case_sha256": sha(case),
        "reviewer": "Protocol control",
        "qualification": "Authored oracle",
        "reviewed_at": "2026-10-22",
        "judgments": [],
    }
    review[binding] = "0" * 64
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="Stale"):
        evaluate(source, key, spec, case, path)
    altered_key = tmp_path / "key.json"
    altered_key.write_bytes(key.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Answer key changed"):
        evaluate(source, altered_key, spec, case)


def test_finalization_and_complete_specification_are_required():
    report, key, spec, sources, _ = fixture(CONTROLS[0])
    report["status"] = "running"
    with pytest.raises(ValueError, match="finalized"):
        assess(report, key, spec, sources, "CONTROL-PATIENT")
    report["status"] = "completed"
    spec.discoveries[0].finding_key = "unknown"
    with pytest.raises(ValueError, match="every expected"):
        assess(report, key, spec, sources, "CONTROL-PATIENT")
