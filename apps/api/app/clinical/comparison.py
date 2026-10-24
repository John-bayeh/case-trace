"""Explicit proposition comparison, separate from citation validity and clinical truth."""

from datetime import datetime

from app.clinical.claims import ClaimComparison, ClinicalClaim
from app.clinical.temporal import reference_day
from app.schemas.investigation import SourceRecord


def compare_claims(a: ClinicalClaim, b: ClinicalClaim, source_b: SourceRecord) -> ClaimComparison:
    result = ClaimComparison(
        claim_a=a,
        claim_b=b,
        relationship="unresolved",
        status="insufficient_evidence",
        reason="Claims are not comparable.",
    )
    if a.patient_id != b.patient_id or not a.patient_id or a.concept != b.concept:
        return result
    if a.subject != "patient" or b.subject != "patient":
        return result
    if a.certainty != "asserted" or b.certainty != "asserted":
        result.status, result.reason = (
            "ambiguous",
            "At least one assertion is uncertain or hypothetical.",
        )
        return result
    if (a.episode_id and b.episode_id and a.episode_id != b.episode_id) or (
        a.episode_scope != "first"
        and (a.episode_scope in {"new", "recurrent"} or b.episode_scope in {"new", "recurrent"})
    ):
        result.status, result.reason = (
            "different_episodes",
            "Episode identity does not support a conflict.",
        )
        return result
    if (
        a.assertion == "onset"
        and b.assertion in {"presence", "worsening"}
        and b.polarity == "positive"
    ):
        result.relationship = "onset_chronology"
        if (
            not a.time.start
            or not b.time.end
            or a.time.precision != "day"
            or b.time.precision != "day"
        ):
            result.status, result.reason = "ambiguous", "Onset comparison lacks exact dates."
            return result
        prior_day = b.time.end
        reference = a.time.reference
        occurrence = b.time.reference
        if reference and occurrence and len(reference) > 10 and len(occurrence) > 10:
            zone = datetime.fromisoformat(reference).tzinfo
            value = datetime.fromisoformat(occurrence)
            if zone is None or value.tzinfo is None:
                return result
            if b.time.basis == "encounter":
                prior_day = value.astimezone(zone).date()
        if prior_day >= a.time.start:
            result.status, result.reason = "compatible", "Earlier presence is not established."
            return result
        entered_raw = source_b.data.get("documented_at") or source_b.data.get("authored_at")
        entered = reference_day(entered_raw)
        if not entered:
            return result
        # Compare calendar days in the onset reference offset, not a collapsed UTC date.
        reference = a.time.reference
        if (
            reference
            and len(reference) > 10
            and isinstance(entered_raw, str)
            and len(entered_raw) > 10
        ):
            zone = datetime.fromisoformat(reference).tzinfo
            value = datetime.fromisoformat(entered_raw)
            if zone is None or value.tzinfo is None:
                return result
            entered = value.astimezone(zone).date()
        if entered >= a.time.start:
            result.status, result.reason = (
                "documentation_delay",
                "Prior occurrence was documented after the reported onset.",
            )
            return result
        same_episode = bool(a.episode_id and a.episode_id == b.episode_id)
        result.status = (
            "documented_conflict"
            if a.episode_scope == "first" or same_episode
            else "potential_conflict"
        )
        result.reason = (
            "Earlier contemporaneous presence conflicts with the reported onset assertion."
        )
        result.assumptions = ["Comparison concerns recorded assertions, not true clinical onset."]
        result.alternatives = ["Retrospective reporting may be inaccurate."]
        if not same_episode and a.episode_scope != "first":
            result.alternatives.append("The sources may concern different episodes.")
        return result
    if (
        a.polarity != b.polarity
        and a.time.start == b.time.start
        and a.time.precision == b.time.precision == "day"
    ):
        result.relationship = "polarity"
        same_encounter = a.anchor.encounter_id and a.anchor.encounter_id == b.anchor.encounter_id
        result.status = "potential_conflict" if same_encounter else "ambiguous"
        result.reason = (
            "Opposing assertions share a day; symptom states may change within that day."
        )
        result.alternatives = ["Different observation times may explain the recorded states."]
    return result
