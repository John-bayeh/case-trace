"""Exact anchor checks shared independently of candidate classification rules."""

from app.schemas.investigation import Anchor, SourceRecord


def anchor_matches(source: SourceRecord, anchor: Anchor) -> bool:
    return (
        source.source == anchor.source
        and source.representation == "source"
        and source.source_version == anchor.source_version
        and source.source_hash == anchor.source_hash
        and source.data.get("encounter_id") == anchor.encounter_id
        and anchor.field in source.data
        and source.data[anchor.field] == anchor.expected
        and (
            anchor.quote is None
            or isinstance(source.data[anchor.field], str)
            and anchor.quote in source.data[anchor.field]
        )
        and (
            anchor.char_start is None
            and anchor.char_end is None
            or isinstance(source.data[anchor.field], str)
            and anchor.char_start is not None
            and anchor.char_end is not None
            and 0 <= anchor.char_start < anchor.char_end <= len(source.data[anchor.field])
            and source.data[anchor.field][anchor.char_start : anchor.char_end] == anchor.quote
        )
    )
