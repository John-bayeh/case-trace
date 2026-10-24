"""Pure source-led chronology rules, shared by proposal and verification."""

import re
from datetime import UTC, date, datetime

from app.clinical.extraction import context_priority, extract_claims
from app.clinical.spans import contextual_span, source_anchor
from app.schemas.investigation import Anchor, Candidate, SourceRecord


def instant(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) <= 10:
        return None
    try:
        result = datetime.fromisoformat(value)
        return result.astimezone(UTC) if result.utcoffset() is not None else None
    except ValueError:
        return None


def anchor(record: SourceRecord, field: str, quote: str | None = None) -> Anchor:
    value = record.data.get(field)
    if quote and isinstance(value, str) and quote in value:
        start = value.index(quote)
        return source_anchor(record, field, *contextual_span(value, start, start + len(quote)))
    return Anchor(
        source=record.source,
        source_version=record.source_version,
        source_hash=record.source_hash,
        encounter_id=record.data.get("encounter_id"),
        field=field,
        expected=record.data.get(field),
        quote=quote,
    )


# Narrow parser: an explicit first-onset assertion, not general clinical NLP.
ONSET = re.compile(
    r"\b([A-Za-z][A-Za-z -]{0,35}?)\s+(?:first\s+)?began on "
    r"([A-Z][a-z]+ \d{1,2}, \d{4});\s*no \1 before then\b",
    re.IGNORECASE,
)


def onset_claim(text: str) -> tuple[str, date, str] | None:
    for match in ONSET.finditer(text):
        try:
            return (
                match[1].strip().casefold(),
                datetime.strptime(match[2], "%B %d, %Y").date(),
                match[0],
            )
        except ValueError:
            continue
    return None


def onset_pair(note: SourceRecord, event: SourceRecord) -> bool:
    claim = onset_claim(str(note.data.get("text_content") or ""))
    occurred = instant(event.data.get("occurred_at"))
    documented = instant(event.data.get("documented_at"))
    note_time = note.data.get("event_at") or note.data.get("authored_at")
    if not claim or not occurred or not documented or not instant(note_time):
        return False
    note_zone = datetime.fromisoformat(str(note_time)).tzinfo
    description = str(event.data.get("description", ""))
    # Match the same symptom as a word and exclude negation; no inference from an absent record.
    mentions = re.search(rf"\b{re.escape(claim[0])}\b", description, re.IGNORECASE)
    negative = re.search(
        rf"\b(?:no|denies|without)\s+(?:\w+\s+){{0,2}}"
        rf"{re.escape(claim[0])}\b",
        description,
        re.IGNORECASE,
    )
    return bool(
        mentions
        and not negative
        and occurred.astimezone(note_zone).date() < claim[1]
        and documented.astimezone(note_zone).date() < claim[1]
    )


def contradictions(notes: list[SourceRecord], events: list[SourceRecord]) -> list[Candidate]:
    candidates = []
    for note in notes:
        for event in events:
            if not onset_pair(note, event):
                continue
            parsed = onset_claim(str(note.data["text_content"]))
            assert parsed is not None
            context = []
            for earlier in notes:
                when = instant(earlier.data.get("event_at"))
                entered = instant(earlier.data.get("authored_at"))
                text = str(earlier.data.get("text_content") or "")
                mention = re.search(rf"\b{re.escape(parsed[0])}\b", text, re.IGNORECASE)
                if (
                    when
                    and entered
                    and when.date() < parsed[1]
                    and entered.date() < parsed[1]
                    and mention
                ):
                    claims = [
                        c
                        for c in extract_claims(earlier)
                        if c.concept == parsed[0]
                        and c.assertion in {"presence", "worsening"}
                        and c.polarity == "positive"
                        and c.subject == "patient"
                        and c.certainty == "asserted"
                        and c.temporality == "current"
                    ]
                    if not claims:
                        continue
                    claims.sort(key=context_priority)
                    item = claims[0].anchor
                    item.relationship = "contextualizes"
                    context.append(item)
            # Both original source documents and event-level timestamps remain reviewable.
            context = context[:8]
            candidates.append(
                Candidate(
                    type="timeline_contradiction",
                    title="Conflicting documented symptom chronology",
                    claim=f"{note.source.id} states {parsed[2]}, while {event.source.id} records "
                    f"{event.data['description']} at {event.data['occurred_at']}.",
                    claim_kind="chronology",
                    rule="onset_conflict",
                    anchors=[
                        anchor(note, "text_content", parsed[2]),
                        anchor(event, "description"),
                        anchor(event, "occurred_at"),
                        anchor(event, "documented_at"),
                        *context,
                    ],
                    alternatives=[
                        "Retrospective history may be inaccurate or describe a new episode."
                    ],
                    limitations=[
                        "A record-level discrepancy does not establish true onset, cause or error."
                    ],
                )
            )
            break  # Earliest sufficient comparison; avoid duplicate same-proposition findings.
    return candidates
