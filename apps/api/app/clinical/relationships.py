"""Conservative cross-record questions with exact linkage and no causal verification."""

import re

from app.clinical.extraction import extract_claims
from app.clinical.rules import anchor, instant
from app.clinical.spans import source_anchor, statements
from app.schemas.investigation import Candidate, SourceRecord


def investigative_relationships(records: list[SourceRecord]) -> list[Candidate]:
    """Compare explicit linked statuses and result-pending assertions.

    Status snapshots need not represent the same moment. These are unresolved
    questions for the existing follow-up agent, not verified medical conclusions.
    """
    rows = sorted(records, key=lambda r: (r.source.type, r.source.id))[:100]
    documents = [r for r in rows if r.source.type == "document" and r.representation == "source"]
    targets = [r for r in rows if r.source.type in {"medication", "referral", "observation"}]
    findings = []
    for document in documents:
        text = document.data.get("text_content") or ""
        if len(text) > 100000:
            continue
        for target in targets:
            if document.data.get("patient_id") != target.data.get("patient_id"):
                continue
            for start, end in statements(text):
                passage = text[start:end]
                if len(passage) > 2000 or not re.search(
                    rf"(?<![\w-]){re.escape(target.source.id)}(?![\w-])", passage
                ):
                    continue
                question = None
                fields = []
                kind = target.source.type
                status = target.data.get("status")
                if kind == "observation" and re.search(
                    r"\b(?:remains? pending|still pending)\b", passage, re.I
                ):
                    available = instant(target.data.get("reported_at"))
                    authored = instant(document.data.get("authored_at"))
                    if (
                        available
                        and authored
                        and available < authored
                        and status in {"final", "corrected"}
                    ):
                        question = (
                            "A linked result is described as pending "
                            "after its recorded availability."
                        )
                        fields = ["status", "reported_at"]
                if kind == "referral":
                    negative = re.search(r"\b(?:not completed|missed|no.show)\b", passage, re.I)
                    positive = re.search(r"\bcompleted\b", passage, re.I) and not negative
                    if (status == "completed" and negative) or (status == "no_show" and positive):
                        question = "Explicit follow-up statements require status reconciliation."
                        fields = ["status", "ordered_at", "appointment_at"]
                if kind == "medication":
                    stopped = re.search(r"\b(?:stopped|discontinued|not taking)\b", passage, re.I)
                    taking = (
                        re.search(r"\b(?:taking|administered|active)\b", passage, re.I)
                        and not stopped
                    )
                    if status == "active" and stopped or status == "discontinued" and taking:
                        question = (
                            "Linked medication states differ; reconcile their "
                            "effective times and reporting context."
                        )
                        fields = ["status", "ordered_at", "start_at", "end_at"]
                if question:
                    citations = [source_anchor(document, "text_content", start, end)]
                    citations.extend(
                        anchor(target, f) for f in fields if target.data.get(f) is not None
                    )
                    if document.data.get("authored_at"):
                        citations.append(anchor(document, "authored_at"))
                    findings.append(
                        Candidate(
                            type="clinical_relationship",
                            title="Linked source assertions require reconciliation",
                            claim=question,
                            claim_kind="interpretation",
                            rule="interpretation",
                            anchors=citations,
                            alternatives=[
                                "The sources may describe different effective times "
                                "or later updates."
                            ],
                            limitations=[
                                "Availability does not establish clinician review."
                                if kind == "observation"
                                else "Status conflict does not establish the true clinical action."
                            ],
                        )
                    )
                    break
            if len(findings) >= 8:
                return findings
    return findings


def medication_associations(records: list[SourceRecord]) -> list[Candidate]:
    """Ask only about a medication explicitly named in a symptom-bearing source."""
    rows = sorted(records, key=lambda r: r.source.id)[:100]
    medications = [r for r in rows if r.source.type == "medication"]
    findings = []
    for row in rows:
        if row.source.type != "document":
            continue
        for claim in extract_claims(row):
            if (
                claim.assertion not in {"presence", "onset", "worsening"}
                or claim.polarity != "positive"
                or claim.subject != "patient"
            ):
                continue
            for medication in medications:
                name = medication.data.get("generic_name") or medication.data.get("medication_name")
                if not name or row.data.get("patient_id") != medication.data.get("patient_id"):
                    continue
                # Linkage must be in the claim's statement, not anywhere in the document.
                if not re.search(rf"\b{re.escape(name)}\b", claim.anchor.quote or "", re.I):
                    continue
                findings.append(
                    Candidate(
                        type="clinical_relationship",
                        title="Medication and symptom relationship requires review",
                        claim=(
                            "A symptom-bearing source names a recorded medication; "
                            "exposure and causality remain unresolved."
                        ),
                        claim_kind="hypothesis",
                        rule="interpretation",
                        anchors=[
                            claim.anchor,
                            *[
                                anchor(medication, f)
                                for f in [
                                    "medication_name",
                                    "status",
                                    "ordered_at",
                                    "start_at",
                                    "end_at",
                                ]
                                if medication.data.get(f) is not None
                            ],
                        ],
                        limitations=[
                            "Ordering does not prove use; chronology does not establish causality."
                        ],
                    )
                )
                if len(findings) >= 4:
                    return findings
    return findings
