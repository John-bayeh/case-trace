# Encounter Retrieval — Skill

## Purpose
Return the chronological and administrative context of a patient's visits, admissions, transfers, and follow-up interactions.

## Inputs
Verified `patient_id`; optional date interval, care setting, facility, encounter status, sort direction, and cursor.

## Procedure
1. Validate patient scope and inclusive/exclusive date-boundary semantics from the API contract.
2. Retrieve encounters with stable `encounter_id`, `patient_id`, facility, type, start/end times, attending role, status and linked source IDs.
3. Preserve difference between event start, discharge and documentation date; never assume charting time equals event time.
4. Sort by explicit timestamp and stable ID tie-breaker, not by display string.
5. Include lightweight links to clinical notes, orders, tests and imaging, but retrieve originals with their dedicated tools.
6. Mark missing/unknown time data explicitly; do not create dates to fill gaps.

## Example
```json
{"encounter_id":"ENC-001","patient_id":"P-001","type":"emergency","started_at":"2026-04-12T09:10:00+03:00","ended_at":"2026-04-12T13:20:00+03:00","status":"completed","linked_record_ids":["NOTE-001","LAB-001"]}
```

## Timeline-specific cautions
Contradictory timestamps are evidence to investigate, **not defects to autocorrect**. Clearly distinguish an event time asserted inside a note from its entered/signed timestamp.

## Tests / done
Verify patient scoping, overlapping encounters, timezone offsets, same-time ordering, pagination, records outside the range, and intentional timeline contradictions. Every encounter is linkable to original records.
