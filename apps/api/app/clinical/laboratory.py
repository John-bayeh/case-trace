"""Identity and recorded reference-range descriptions, without clinical inference."""

from app.schemas.investigation import SourceRecord


def analyte_key(record: SourceRecord) -> tuple[str, str, str] | None:
    code, name, unit = (record.data.get(k) for k in ("test_code", "test_name", "unit"))
    if not unit or not (code or name):
        return None
    return ("code" if code else "name", str(code or name).casefold(), str(unit))


def range_description(record: SourceRecord) -> str:
    value = record.data.get("value_numeric")
    low, high = (record.data.get(k) for k in ("reference_range_low", "reference_range_high"))
    if value is None or low is None and high is None:
        return "Reference interval not recorded."
    if low is not None and value < low:
        return "Below the recorded reference interval."
    if high is not None and value > high:
        return "Above the recorded reference interval."
    return "Within the available recorded reference bounds."
