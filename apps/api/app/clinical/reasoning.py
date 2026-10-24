"""Bounded candidate construction from source claims; no retrieval or evaluator access."""

from collections import Counter

from app.clinical.comparison import compare_claims
from app.clinical.extraction import context_priority, extract_claims
from app.clinical.rules import anchor
from app.schemas.investigation import Candidate, SourceRecord

MAX_SOURCES = 100
MAX_PAIRS = 4096


def reasoning_limitations(records: list[SourceRecord]) -> list[str]:
    limits = []
    if len(records) > MAX_SOURCES:
        limits.append("Reasoning source budget reached; additional sources were not compared.")
    claims = []
    for record in records[:MAX_SOURCES]:
        text = str(record.data.get("text_content") or record.data.get("description") or "")
        if len(text) > 100000:
            limits.append("A narrative exceeded the extraction text budget and was not processed.")
        extracted = extract_claims(record)
        if len(extracted) >= 64:
            limits.append(
                "A source reached the claim budget; additional mentions may be unprocessed."
            )
        claims.extend(extracted)
    counts = Counter(c.concept for c in claims)
    estimated = sum(
        counts[a.concept]
        for a in claims
        if a.assertion in {"onset", "presence", "worsening"} and a.polarity == "positive"
    )
    if estimated > MAX_PAIRS:
        limits.append("Comparison budget may truncate candidate pairs; coverage is incomplete.")
    return list(dict.fromkeys(limits))


def structured_contradictions(
    notes: list[SourceRecord], events: list[SourceRecord]
) -> list[Candidate]:
    sources = sorted(
        {(r.source.type, r.source.id): r for r in notes + events}.values(),
        key=lambda r: (
            str(r.data.get("occurred_at") or r.data.get("event_at") or "~"),
            r.source.id,
        ),
    )[:MAX_SOURCES]
    extracted = [(r, extract_claims(r)) for r in sources]
    findings: list[Candidate] = []
    pairs = 0
    seen = set()
    for source, claims in extracted:
        for a in claims:
            if a.assertion not in {"onset", "presence", "worsening"} or a.polarity != "positive":
                continue
            for other, prior in extracted:
                if source.source == other.source:
                    continue
                for b in prior:
                    if a.concept != b.concept:
                        continue
                    pairs += 1
                    if pairs > MAX_PAIRS:
                        return findings
                    comparison = compare_claims(a, b, other)
                    if comparison.status not in {"documented_conflict", "potential_conflict"}:
                        continue
                    key = (a.id, a.concept, comparison.relationship)
                    if key in seen:
                        continue
                    seen.add(key)
                    anchors = [a.anchor, b.anchor]
                    for row in (source, other):
                        for field in ("event_at", "authored_at", "occurred_at", "documented_at"):
                            if row.data.get(field):
                                anchors.append(anchor(row, field))
                    # Context must be a positive contemporaneous assertion, never just a token hit.
                    for context, context_claims in extracted:
                        if context.source in (source.source, other.source):
                            continue
                        if any(
                            x.source == context.source and x.field == "text_content"
                            for x in anchors
                        ):
                            continue
                        for c in sorted(context_claims, key=context_priority):
                            if compare_claims(a, c, context).status == "documented_conflict":
                                item = c.anchor.model_copy(
                                    update={"relationship": "contextualizes"}
                                )
                                anchors.append(item)
                                break
                        if len(anchors) >= 16:
                            break
                    findings.append(
                        Candidate(
                            type="timeline_contradiction",
                            title="Conflicting documented symptom chronology",
                            claim=(
                                f"{a.anchor.source.id}: {a.anchor.quote} "
                                f"Compared with {b.anchor.source.id}: {b.anchor.quote}"
                            )[:2000],
                            claim_kind="chronology",
                            rule="onset_conflict"
                            if comparison.status == "documented_conflict"
                            else "interpretation",
                            anchors=anchors,
                            alternatives=comparison.alternatives,
                            limitations=[
                                comparison.reason,
                                "Clinical truth and causality remain unresolved.",
                            ],
                        )
                    )
                    if len(findings) == 20:
                        return findings
    return findings
