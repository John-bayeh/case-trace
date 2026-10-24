# Medication Retrieval — Skill

## Purpose
Expose accurate longitudinal medication evidence for reconciliation and timeline investigations.

## Inputs
Scoped `patient_id`; optional encounter, medication identifier, time range, record class, status, cursor.

## Keep record classes distinct
1. Prescription / medication order
2. Medication dispense or pharmacy fill (if synthetic fixture includes it)
3. Medication administration record (MAR)
4. Patient-reported medication history or reconciliation
5. Discontinuation, hold, dose change, or allergy-related note

A prescribed drug **does not prove administration**, and a patient report **does not prove compliance**.

## Procedure
1. Fetch records with source IDs and source type clearly labeled.
2. Preserve drug name/normalized code where provided, route, strength, dose, unit, frequency, indication (if present), start/end, author and status.
3. Distinguish `ordered_at`, `effective_from`, `administered_at`, `discontinued_at`, and charted time.
4. Return order modification chains rather than merging into a single apparently continuous regimen.
5. Link contradictory narratives back to the exact note, order or MAR entry.
6. Report incomplete evidence as `unknown`, not `no medication`.

## Example
```json
{"medication_record_id":"MED-012","record_type":"order","patient_id":"P-001","drug_display":"Demo medication","dose":"5 mg","route":"oral","ordered_at":"2026-04-12T09:20:00+03:00","status":"discontinued","source_document_id":"DOC-016"}
```

## Forbidden behavior
Do not infer adherence or causality from order lists; do not generate prescribing advice; do not merge discontinued and active doses.

## Tests / done
Validate order vs. administration distinction, overlaps, stop/restart, modifications, incomplete reports, provenance, temporal filters and access control.
