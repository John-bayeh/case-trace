# Timeline Reconstruction Skill

## Purpose
Build an auditable sequence from fragmented records, separating *when something happened* from *when it was recorded or imported*.

## Timeline event shape
`event_id`, `patient_id`, `event_type`, `event_at` (nullable), `time_precision` (`instant|day|month|range|unknown`), `timezone?`, `recorded_at?`, `imported_at?`, `start_at?`, `end_at?`, `actor?`, `description`, `evidence_ids[]`, `temporal_conflicts[]`, `source_confidence`, `normalization_notes[]`.

## Workflow
1. Extract dates: visit service date, symptom onset reported by patient, test ordered/collected/resulted, medication ordered/dispensed/administered/stopped, note signed, document scanned.
2. Assign explicit semantic role to each timestamp; preserve the unmodified raw value.
3. Normalize formats/timezones with conservative assumptions; never fabricate time-of-day for date-only entries.
4. Sort deterministic display order by earliest possible event time, then source priority and stable ID; show ranges/unknown position visibly.
5. Link events to encounter and evidence IDs; merge exact duplicates only if clinically equivalent and same underlying event.
6. Identify impossible or suspicious intervals (e.g., signed before encounter; reported outcome before sample collection), and forward as candidates, not definitive errors.
7. Annotate interval uncertainty from ambiguous phrases such as “last week” or retrospective symptom histories.

## Temporal logic
Support `before`, `after`, `overlaps`, `same_day`, `uncertain`. Compare interval bounds, not just ISO strings. Keep date-only and exact timestamps distinguishable; consider timezone, backdating, late entry, and amendments as alternative explanations.

## Testing / done
Fixtures cover DST/timezone offsets, partial dates, note addenda, retrospective report, conflicting sample/result times, and reordered import dates. Timeline is stable across runs and each event opens its originating source.
