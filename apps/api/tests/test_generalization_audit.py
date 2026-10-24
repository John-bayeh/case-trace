"""Reproducible frozen audit controls, separate from investigator runtime."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = ROOT / "docs/evaluation/artifacts/generalization"
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_investigation import evaluate  # noqa: E402


def test_frozen_cohort_inputs_are_unchanged():
    hashes = json.loads((ARTIFACTS / "hashes.json").read_text())
    assert len(hashes) >= 138
    for name, expected in hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name


@pytest.mark.parametrize("case", [f"CASE-{n:03}" for n in range(1, 7)])
def test_replay_artifacts_have_resolvable_trace_coverage_and_unchanged_scoring(case):
    for phase in ["before", "after"]:
        directory = ARTIFACTS / phase / case
        measured = json.loads((directory / "score.json").read_text())
        assert (
            evaluate(directory / "report.json", ROOT / "evaluation" / case / "answer-key.json")
            == measured["score"]
        )
        assert measured["unsupported_verified_findings"] == 0
        assert measured["failed_evidence_checks"] == 0
        tools = json.loads((directory / "tools.json").read_text())
        report = json.loads((directory / "report.json").read_text())
        identifiers = {t["id"] for t in tools["items"]} | {
            f["id"]
            for group in ["verified_findings", "unresolved_findings", "rejected_findings"]
            for f in report[group]
        }
        coverage = json.loads((ARTIFACTS / phase / "coverage.json").read_text())
        rows = [r for r in coverage if r["case_id"] == case]
        assert rows
        for row in rows:
            assert row["exists"] and row["retrievable"] and row["cross_patient_denied"]
            assert set(row["supporting_trace_ids"]) <= identifiers
            assert row["considered"] == "not_observable"
        if case == "CASE-001":
            assert measured["score"]["discovery_grade"] == "exact"
            assert measured["score"]["required_source_coverage"] == "6/6"


def test_source_coverage_is_not_misrepresented_as_semantic_discovery():
    measured = json.loads((ARTIFACTS / "after/CASE-006/score.json").read_text())
    assert measured["score"]["required_source_coverage"] == "3/3"
    assert not measured["score"]["expected_discovery_detected"]
    assert measured["score"]["discovery_grade"] == "failure"
