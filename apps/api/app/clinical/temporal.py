"""Conservative narrative date intervals; source timestamps are retained literally."""

import calendar
import re
from datetime import date, datetime, timedelta

from app.clinical.claims import ClaimTime

MONTHS = {name.casefold(): index for index, name in enumerate(calendar.month_name) if name}
MONTH = "(?:" + "|".join(calendar.month_name[1:]) + ")"
EXPLICIT = re.compile(rf"\b({MONTH})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?\b", re.I)
RELATIVE = re.compile(
    r"\b(?:(about|approximately)\s+)?(\d+|one|two|three|four)\s+"
    r"(days?|weeks?)\s+(?:ago|before (?:the |this )?(?:visit|encounter))\b",
    re.I,
)


def reference_day(raw: object) -> date | None:
    if not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw) if len(raw) == 10 else datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def narrative_time(text: str, reference: str | None) -> ClaimTime:
    ref = reference_day(reference)
    if ref and re.search(r"\blast month\b", text, re.I):
        previous_month = ref.month - 1 or 12
        previous_year = ref.year - int(ref.month == 1)
        return ClaimTime(
            start=date(previous_year, previous_month, 1),
            end=date(
                previous_year, previous_month, calendar.monthrange(previous_year, previous_month)[1]
            ),
            precision="month",
            basis="relative",
            reference=reference,
            original="last month",
        )
    match = EXPLICIT.search(text)
    if match:
        year = int(match[3]) if match[3] else ref.year if ref else None
        if year is not None:
            try:
                day = date(year, MONTHS[match[1].casefold()], int(match[2]))
                approximate = bool(
                    re.search(r"\b(?:about|around|approximately)\b", text[: match.start()])
                )
                return ClaimTime(
                    start=day,
                    end=day,
                    precision="approximate" if approximate else "day",
                    basis="explicit",
                    reference=reference,
                    original=match[0],
                )
            except ValueError:
                pass  # Invalid source date is retained as unknown, never repaired.
        return ClaimTime(original=match[0], reference=reference)
    relative = RELATIVE.search(text)
    if relative:
        if ref:
            words = {"one": 1, "two": 2, "three": 3, "four": 4}
            count = words.get(relative[2].casefold())
            count = count if count is not None else int(relative[2])
            delta = count * (7 if relative[3].casefold().startswith("week") else 1)
            if delta <= 36500:
                center = ref - timedelta(days=delta)
                tolerance = 3 if relative[3].casefold().startswith("week") else 1
                return ClaimTime(
                    start=center - timedelta(days=tolerance),
                    end=center + timedelta(days=tolerance),
                    precision="approximate",
                    basis="relative",
                    reference=reference,
                    original=relative[0],
                )
        return ClaimTime(original=relative[0], reference=reference, basis="relative")
    month = re.search(rf"\b(?:(early|mid|late)\s+)?({MONTH})(?:\s+(\d{{4}}))?\b", text, re.I)
    if month and (month[3] or ref):
        year = int(month[3]) if month[3] else ref.year if ref else 0
        number = MONTHS[month[2].casefold()]
        first, last = {
            "early": (1, 10),
            "mid": (11, 20),
            "late": (21, calendar.monthrange(year, number)[1]),
        }.get((month[1] or "").casefold(), (1, calendar.monthrange(year, number)[1]))
        return ClaimTime(
            start=date(year, number, first),
            end=date(year, number, last),
            precision="month",
            basis="historical",
            reference=reference,
            original=month[0],
        )
    return ClaimTime(reference=reference)
