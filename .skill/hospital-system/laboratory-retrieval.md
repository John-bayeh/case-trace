# Laboratory Retrieval — Skill

## Purpose
Retrieve ordered tests, specimens, analyte results, reference intervals, critical flags, and amended reports without losing laboratory provenance.

## Inputs
Scoped `patient_id`; optional `encounter_id`, order/test codes, date range, abnormal-only flag, status, and cursor.

## Required distinctions
- `ordered_at` / `collected_at` / `received_at` / `resulted_at` / `reported_at`
- specimen identifier and type
- analyte code, display label, numeric or textual value, unit, reference interval and interpretation flag
- preliminary, final, corrected and cancelled result status
- authorizing laboratory, original document/report ID, correction lineage

## Procedure
1. Resolve patient access and test identity against the schema.
2. Filter by specified time axis (e.g., specimen collection vs. report time), naming it in outputs.
3. Return panels and component results with immutable IDs; preserve units as recorded.
4. If an amended result exists, return its lineage; never overwrite the earlier result silently.
5. Preserve qualitative tests, nulls and out-of-range flags; do not coerce `NEGATIVE` to a number.
6. Link each result to the source report/document and specimen/encounter when available.

## Example
```json
{"result_id":"LABR-042","order_id":"LABO-009","encounter_id":"ENC-003","analyte":"potassium","value":4.1,"unit":"mmol/L","collected_at":"2026-04-12T10:00:00+03:00","reported_at":"2026-04-12T11:08:00+03:00","status":"final","source_document_id":"DOC-010"}
```

## Forbidden behavior
Do not recompute or relabel reference ranges as clinical diagnoses, discard superseded results, mix incompatible units, or imply an order proves a test was completed.

## Tests / done
Panel grouping, range boundary handling, abnormal flag semantics, corrections, missing specimens, timestamp ordering, unit preservation, permission scope and result-to-document navigation all pass.
