"""Exact statement locators over original Unicode text; never normalized offsets."""

import re

from app.schemas.investigation import Anchor, SourceRecord


def statements(text: str) -> list[tuple[int, int]]:
    spans = []
    cursor = 0
    boundaries = [m.end() for m in re.finditer(r"[.!?]+(?=\s|$)|\n", text)]
    for boundary in [*boundaries, len(text)]:
        start, end = cursor, boundary
        cursor = boundary
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((start, end))
    return spans


def contextual_span(text: str, start: int, end: int) -> tuple[int, int]:
    for left, right in statements(text):
        if left <= start < end <= right:
            return left, right
    return start, end


def source_anchor(record: SourceRecord, field: str, start: int, end: int) -> Anchor:
    text = record.data[field]
    if not isinstance(text, str) or not 0 <= start < end <= len(text):
        raise ValueError("INVALID_SOURCE_SPAN")
    if end - start > 2000:
        raise ValueError("SOURCE_STATEMENT_EXCEEDS_ANCHOR_BUDGET")
    return Anchor(
        source=record.source,
        source_version=record.source_version,
        source_hash=record.source_hash,
        encounter_id=record.data.get("encounter_id"),
        field=field,
        expected=text,
        quote=text[start:end],
        char_start=start,
        char_end=end,
    )
