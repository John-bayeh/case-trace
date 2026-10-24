"""Bounded longitudinal observations, without diagnosis, exposure or causality inference."""

from collections import defaultdict

from app.clinical.laboratory import analyte_key, range_description
from app.clinical.rules import anchor, instant
from app.schemas.investigation import Anchor, Candidate, SourceRecord


def record_series(records: list[SourceRecord]) -> list[Candidate]:
    groups: dict[tuple[str, ...], list[SourceRecord]] = defaultdict(list)
    documents = {
        r.source.id: r
        for r in records
        if r.source.type == "document" and r.representation == "source"
    }
    for row in records:
        if row.representation != "source":
            continue
        patient = str(row.data.get("patient_id"))
        if row.source.type == "observation":
            identity = analyte_key(row)
            if (
                identity
                and row.data.get("value_numeric") is not None
                and instant(row.data.get("specimen_collected_at"))
            ):
                groups[(patient, "observation", *identity)].append(row)
        elif row.source.type == "medication":
            name = row.data.get("generic_name") or row.data.get("medication_name")
            if name and row.data.get("status") and instant(row.data.get("ordered_at")):
                groups[(patient, "medication", str(name).casefold())].append(row)
    results = []
    for key, rows in sorted(groups.items()):
        lab = key[1] == "observation"
        time_field = "specimen_collected_at" if lab else "ordered_at"
        rows.sort(key=lambda r: (instant(r.data[time_field]), r.source.id))
        # Keep all decisive values/ranges and source links within 20 anchors.
        # Overlap one point so relationships remain connected across chunk boundaries.
        size = 3 if lab else 4
        for start in range(0, len(rows) - 1, size - 1):
            batch = rows[start : start + size]
            if len({r.data.get("encounter_id") for r in batch}) < 2:
                continue
            abnormal = [
                r
                for r in batch
                if lab
                and range_description(r)
                in {
                    "Below the recorded reference interval.",
                    "Above the recorded reference interval.",
                }
            ]
            if lab and len(abnormal) < 2:
                continue
            if not lab and len({r.data["status"] for r in batch}) < 2:
                continue
            citations: list[Anchor] = []
            observations = []
            for row in batch:
                fields = (
                    [
                        "value_numeric",
                        "unit",
                        "specimen_collected_at",
                        "reference_range_low",
                        "reference_range_high",
                    ]
                    if lab
                    else ["medication_name", "status", "ordered_at"]
                )
                citations.extend(
                    anchor(row, field) for field in fields if row.data.get(field) is not None
                )
                if lab and row is batch[0]:
                    citations.extend(
                        anchor(row, f)
                        for f in ["test_name", "test_code"]
                        if row.data.get(f) is not None
                    )
                if lab:
                    observations.append(
                        f"{row.source.id}: {row.data['value_numeric']} {row.data['unit']} "
                        f"at {row.data[time_field]}; {range_description(row)}"
                    )
                else:
                    observations.append(
                        f"{row.source.id}: {row.data['status']} ordered {row.data[time_field]}"
                    )
                document = documents.get(str(row.data.get("source_document_id")))
                if document and document.data.get("patient_id") == row.data.get("patient_id"):
                    citation = anchor(document, "text_content")
                    citation.relationship = "contextualizes"
                    if not any(a.source == citation.source for a in citations):
                        citations.append(citation)
            name = batch[0].data["test_name" if lab else "medication_name"]
            results.append(
                Candidate(
                    type="laboratory_change" if lab else "medication_change",
                    title=f"Longitudinal recorded {'abnormalities' if lab else 'statuses'}: {name}",
                    claim=f"{name}: " + "; ".join(observations),
                    claim_kind="observation",
                    rule="record_series",
                    anchors=citations,
                    limitations=[
                        "Recorded reference bounds are source-specific; fasting status and "
                        "specimen context require review. Repeated abnormalities do not "
                        "establish a diagnosis."
                        if lab
                        else "Different order snapshots may represent intended changes. Orders, "
                        "patient reports and medication lists do not establish actual ingestion "
                        "or causality."
                    ],
                )
            )
    return results
