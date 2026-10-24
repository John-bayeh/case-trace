# CASE-002 Generation Report

## Status

This report records the deterministic generation and verification results. No
medical expert validation is claimed.

## Dataset

CASE-002, **The Medication List That Never Caught Up**, uses one synthetic
patient and seven encounters from January through May 2026. It includes
medication orders and statements, reconciliation records, serial renal
laboratory panels, clinical notes, a nephrology referral, and readable PDF
source documents. Imaging is intentionally omitted because it does not
contribute to this medication-and-laboratory investigation.

## Evidence design

The primary finding is a documentation discrepancy between the February
lisinopril discontinuation/order change and later records that retain or report
lisinopril. The secondary finding is a creatinine/eGFR/potassium trend with
partial recovery. The evaluator key rejects definitive medication-induced kidney
injury and confirmed ingestion claims.

## Reproducibility

Generate with:

```text
uv run --group case-data python scripts/generate_case002.py
```

The generator creates canonical JSON, a checksum manifest, evaluator-only
ground truth, and 20 one-page PDF documents. It does not download or generate
medical images and does not modify CASE-001.

## Actual validation results

Commands were run from `apps/api` with the repository's existing `uv` environment:

```text
uv run --group case-data python ..\..\scripts\generate_case002.py
uv run python -m app.hospital.cli validate CASE-002 --format json
uv run ruff check ..\..\scripts\generate_case002.py
uv run mypy ..\..\scripts\generate_case002.py
```

Results:

- Canonical validation: passed with 7 encounters, 6 clinical events, 25
  observations, 11 medication records, 20 documents, 5 laboratory reports,
  1 referral, 3 diagnoses, 1 symptom, and no imaging assets. The validator
  emitted six cross-encounter provenance warnings for laboratory results,
  which are expected because specimen/report records belong to the laboratory
  encounter while the clinical event that prompted them belongs to another
  encounter.
- Asset validation: passed for 20 readable PDF assets; no image assets were
  created or registered.
- Ruff: passed.
- mypy: passed for the generator.

## Isolated ingestion and investigation

An isolated migrated SQLite database was used at
`data/runtime/case002-validation.db`; the normal runtime database was not
reset. CASE-002 imported successfully, and a second import returned
`status: unchanged` with the same import ID and source hash. A separate fresh
database imported CASE-001 version 1.1 and CASE-002 version 1.0 consecutively,
with distinct patient and import identifiers.

The existing investigation runner completed CASE-002 with status
`completed_with_limitations`, 15 verified findings, and no failed verification
checks. The existing evaluator reported `discovery_grade: failure`: it cited
the discontinuation and old-bottle sources but did not detect either expected
discovery as a consolidated finding and covered 2/10 required source IDs.
This is recorded as an investigation-engine baseline limitation, not hidden or
corrected by changing prompts, scoring, or the case key.

The backend regression suite completed with 277 passed, 1 skipped, and 2
failures in the pre-existing CASE-001 investigation test. Both failures assert
the old CASE-001 evaluator dataset version `1.0`, while the repository's
finalized CASE-001 answer key is version `1.1`. No CASE-001 files were modified
for CASE-002, so that unrelated expectation was not changed here.
