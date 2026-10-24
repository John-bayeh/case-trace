"""Bounded source comparisons, never autonomous diagnoses or treatment advice."""

import re

from app.clinical.claims import ClinicalClaim
from app.clinical.diagnostic_models import (
    ComparisonVerdict,
    DiagnosticCertainty,
    DiagnosticComparison,
    DiagnosticEvidence,
)
from app.clinical.relationship_models import RelationshipEvidence
from app.clinical.result_models import ResultSearchScope
from app.clinical.rules import anchor, instant
from app.core.provenance import digest
from app.schemas.investigation import Candidate, Hypothesis, SourceRecord

LIMITATIONS = [
    "Working assessments are clinician documentation, not established clinical truth.",
    "Verification establishes a source relationship; the clinical question remains provisional.",
    "A single test does not exclude coexisting explanations or establish a final diagnosis.",
    "No probability, treatment instruction or clinician-impropriety conclusion is established.",
    "Accessible records and explicit extraction vocabulary limit the comparison.",
]
SYMPTOMS = re.compile(
    r"\b(palpitations?|syncope|dizziness|dyspnea|chest pain|fatigue|cough)\b", re.I
)
TEST = re.compile(
    r"\b(?:monitor|ecg|electrocardiogram|echocardiogram|imaging|spirometry|test result)\b", re.I
)
FINDING = re.compile(r"\b(?:tachycardia|arrhythmia|abnormal(?:ity)?|obstruction|ischemia)\b", re.I)


def working_assessment(row: SourceRecord) -> tuple[str, DiagnosticCertainty] | None:
    if row.source.type != "document" or row.representation != "source":
        return None
    text = str(row.data.get("text_content") or "")
    patterns = [
        r"\b(?:working (?:diagnosis|explanation)|provisional diagnosis|suspected diagnosis)"
        r"\s*(?:is\s+|of\s+|:\s*)?([A-Za-z][A-Za-z -]{1,50}?)"
        r"(?=[.;,\n]|\s+(?:and|with|because)\b|$)",
        r"\binitial assessment documents ([A-Za-z][A-Za-z -]{1,50}?)"
        r"(?=[.;,\n]|\s+(?:and|with)\b|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        prefix = re.split(r"[.!?\n]", text[: match.start()])[-1]
        if re.search(
            r"\b(?:family history|mother|father|sister|brother)\b", prefix, re.I
        ) or re.search(r"\b(?:no|not|without)\s+$", prefix, re.I):
            continue
        name = match[1].strip().casefold()
        if name in {"recorded", "documented", "unknown", "unclear"} or re.search(
            r"\b(?:not|no|ruled out|family|mother|father)\b", match[0], re.I
        ):
            continue
        certainty: DiagnosticCertainty = (
            "provisional"
            if "provisional" in match[0].lower()
            else (
                "suspected"
                if "suspected" in match[0].lower()
                else "documented_assessment_unknown_certainty"
            )
        )
        return name, certainty
    return None


def symptoms(text: str) -> set[str]:
    return {
        m[0].lower().rstrip("s")
        for m in SYMPTOMS.finditer(text)
        if not re.search(r"\b(?:no|denies|without)\s+(?:\w+\s+){0,2}$", text[: m.start()], re.I)
    }


def add(evidence: list[DiagnosticEvidence], row: SourceRecord, role: str) -> None:
    field = "text_content" if row.source.type == "document" else "reason"
    if not row.data.get(field) or len(str(row.data[field])) > 2000:
        return
    if any(e.anchor.source == row.source for e in evidence):
        return
    evidence.append(
        DiagnosticEvidence(
            role=role,  # type: ignore[arg-type]
            attribution="nonspecific_context"
            if role in {"reassessment", "test_order", "referral"}
            else "explicit",
            anchor=anchor(row, field),
            timestamps={k: v for k, v in row.data.items() if k.endswith("_at")},
        )
    )


def diagnostic_comparisons(rows: list[SourceRecord], search: ResultSearchScope) -> list[Candidate]:
    documents = sorted(
        [r for r in rows if r.source.type == "document" and r.representation == "source"],
        key=lambda r: r.source.id,
    )
    working = [(r, w) for r in documents if (w := working_assessment(r))]
    names = sorted({w[0] for _, w in working})[:3]
    results = []
    for name in names:
        assessments = [r for r, w in working if w[0] == name]
        symptom_context = [
            r
            for r in documents
            if r.data.get("document_type")
            not in {
                "diagnostic_report",
                "cardiology_report",
                "radiology_report",
                "laboratory_report",
            }
            and r.data.get("encounter_id")
            and any(r.data.get("encounter_id") == a.data.get("encounter_id") for a in assessments)
            and symptoms(str(r.data.get("text_content") or ""))
        ]
        terms = set().union(
            *(
                symptoms(str(r.data.get("text_content") or ""))
                for r in assessments + symptom_context
            )
        )
        if not terms:
            continue
        objective = [
            r
            for r in documents
            if r.data.get("document_type")
            in {"diagnostic_report", "cardiology_report", "radiology_report", "laboratory_report"}
            and TEST.search(str(r.data.get("text_content") or ""))
        ]
        if not objective:
            continue
        evidence: list[DiagnosticEvidence] = []

        for r in assessments:
            add(evidence, r, "working_assessment")
        for r in symptom_context:
            add(evidence, r, "symptom_context")
        weakening, supporting, contradictions = [], [], []
        missing = [
            "Original test data and episode-level symptom correlation require clinical review.",
            "Whether the working explanation and another mechanism coexist remains unresolved.",
        ]
        states: dict[str, str] = {}
        for row in objective:
            text = str(row.data.get("text_content") or "")
            links = [
                r
                for r in rows
                if r.source.type == "diagnostic_report"
                and r.data.get("document_id") == row.source.id
            ]
            mismatch = any(
                not r.data.get("encounter_id")
                or r.data.get("encounter_id") != row.data.get("encounter_id")
                for r in links
            )
            at = instant(row.data.get("event_at"))
            preceding = any(
                (wt := instant(r.data.get("event_at"))) and at and wt <= at for r in assessments
            )
            correlated = bool(terms & symptoms(text)) and bool(
                re.search(
                    r"\b(?:patient.triggered|correlat\w* with|during symptoms|"
                    r"symptom.associated)\b",
                    text,
                    re.I,
                )
            )
            incidental = bool(
                re.search(r"\b(?:incidental|unrelated to symptoms|asymptomatic)\b", text, re.I)
            )
            uncertain = bool(
                re.search(
                    r"\b(?:inconclusive|non.diagnostic|artifact|possible artifact)\b", text, re.I
                )
            )
            negative = bool(
                re.search(
                    r"\b(?:no|without|not)\s+(?:\w+\s+){0,2}"
                    r"(?:arrhythmia|tachycardia|abnormal(?:ity)?)\b",
                    text,
                    re.I,
                )
            )
            if re.search(
                r"\b(?:mother|father|family member)\b.{0,30}\b(?:monitor|test)\b", text, re.I
            ):
                uncertain = True
            positive = (
                bool(FINDING.search(text))
                and not negative
                and bool(re.search(r"\b(?:captured|showed|demonstrated|detected)\b", text, re.I))
            )
            supports = bool(
                re.search(
                    r"\b(?:supports?|consistent with)\s+(?:the working diagnosis of\s+)?"
                    rf"{re.escape(name)}\b",
                    text,
                    re.I,
                )
            )
            state = (
                "uncertain"
                if mismatch or uncertain or not preceding
                else (
                    "incidental"
                    if incidental
                    else "supportive"
                    if supports
                    else "weakening"
                    if positive and correlated
                    else "negative"
                    if negative
                    else "unrelated"
                )
            )
            states[row.source.id] = state
            add(
                evidence,
                row,
                "supporting_interpretation"
                if state == "supportive"
                else "objective_interpretation",
            )
            if state == "weakening":
                weakening.append(anchor(row, "text_content"))
            if state == "supportive":
                supporting.append(anchor(row, "text_content"))
            if mismatch:
                missing.append(
                    "A result/document encounter link is inconsistent; "
                    "the original test identity needs clarification."
                )
            if not links:
                missing.append(
                    "The original interpretation has no matching structured report link; "
                    "its result metadata remains unverified."
                )
        # Conflicting interpretations need an actual shared test context, not just
        # different results across the patient's history.
        for left in objective:
            for right in objective:
                if states[left.source.id] != "weakening" or states[right.source.id] not in {
                    "negative",
                    "supportive",
                }:
                    continue
                same_context = left.data.get("encounter_id") and left.data.get(
                    "encounter_id"
                ) == right.data.get("encounter_id")
                if (
                    same_context
                    and (left_test := TEST.search(str(left.data.get("text_content"))))
                    and (right_test := TEST.search(str(right.data.get("text_content"))))
                    and left_test[0].casefold() == right_test[0].casefold()
                ):
                    contradictions.append(anchor(right, "text_content"))
        # Generic specialist/reassessment notes are retained as context only. No
        # clinical interpretation or later chronology is invented from them.
        if len(names) == 1:
            for row in documents:
                text = str(row.data.get("text_content") or "")
                if row.data.get("document_type") == "diagnostic_order":
                    add(evidence, row, "test_order")
                elif re.search(
                    r"\b(?:specialist review|compares the new evidence|reassessment)\b", text, re.I
                ):
                    add(evidence, row, "reassessment")
            for row in rows:
                if row.source.type == "referral" and re.search(
                    r"\b(?:rhythm|diagnostic|evaluation)\b", str(row.data.get("reason") or ""), re.I
                ):
                    add(evidence, row, "referral")
        verdict: ComparisonVerdict = (
            "inconclusive"
            if contradictions or any(s == "uncertain" for s in states.values())
            else ("reconsideration_question" if weakening else "not_challenged")
        )
        if contradictions:
            missing.append(
                "Conflicting interpretations need reconciliation against "
                "the original test and symptom diary."
            )
        if not weakening:
            missing.append(
                "No unambiguous symptom-correlated contradictory "
                "objective interpretation was established."
            )
        question = (
            (
                f"Does {name} fully explain the recorded symptoms and symptom-associated objective "
                "interpretation, or are additional explanations needed?"
            )
            if verdict == "reconsideration_question"
            else (
                "What further source evidence would clarify the sufficiency "
                f"of the documented {name} explanation?"
            )
        )
        if len(evidence) > 20 or len(evidence) < 2:
            continue
        comparison = DiagnosticComparison(
            hypothesis=name,
            certainty=next(iter(certainties))
            if len(certainties := {w[1] for r, w in working if r in assessments}) == 1
            else "documented_assessment_unknown_certainty",
            evidence=evidence,
            supporting_evidence=supporting[:10],
            weakening_evidence=weakening[:10],
            contradictory_evidence=contradictions[:10],
            missing_evidence=list(dict.fromkeys(missing))[:10],
            alternatives=[
                "The working explanation and another mechanism may coexist; "
                "neither is established here.",
                "Incidental findings, interpretation disagreement or incomplete "
                "symptom correlation remain possible.",
            ],
            question=question,
            provisional_verdict=verdict,
            search=search,
        )
        selected = evidence[:8]
        assertions = [
            ClinicalClaim(
                id="DC-" + digest(e.model_dump(mode="json"))[:24],
                patient_id=assessments[0].data.get("patient_id"),
                anchor=e.anchor,
                concept=name,
                original_concept=name,
                assertion="impression",
                value=e.role,
                origin="clinician_interpretation"
                if "interpretation" in e.role
                else "clinician_record",
                certainty="uncertain",
                timestamps=e.timestamps,
                documentation_time_field="authored_at"
                if e.anchor.source.type == "document"
                else None,
                event_time_field="event_at" if e.anchor.source.type == "document" else "ordered_at",
            )
            for e in selected
        ]
        claim = (
            "The documented working assessment and original test interpretations support a "
            f"provisional comparison ({verdict}). {question} "
            "This does not exclude the working explanation, establish a final "
            "diagnosis or imply improper care."
        )
        results.append(
            Candidate(
                type="clinical_relationship",
                title="Evidence-based working hypothesis comparison",
                claim=claim,
                claim_kind="observation",
                rule="clinical_relationship",
                anchors=[e.anchor for e in evidence],
                relationship=RelationshipEvidence(
                    relationship_type="hypothesis_challenge",
                    diagnostic_comparison=comparison,
                    assertions=assertions,
                    supporting_assertion_ids=[a.id for a in assertions],
                    unresolved_questions=[question],
                ),
                limitations=LIMITATIONS,
                alternatives=comparison.alternatives,
            )
        )
    return results


def comparison_hypothesis(comparison: DiagnosticComparison) -> Hypothesis:
    """Called only after the complete comparison has independently verified."""
    return Hypothesis(
        comparison=comparison,
        explanation=comparison.question,
        supports=comparison.supporting_evidence,
        weakens=comparison.weakening_evidence,
        missing_evidence=comparison.missing_evidence,
        alternatives=comparison.alternatives,
        limitations=LIMITATIONS,
        verdict="inconclusive",
    )
