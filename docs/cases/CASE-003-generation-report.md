# CASE-003 Generation Report

Status: structurally valid and imported into the isolated validation database.

- Generator: `scripts/generate_cases003_006.py`
- Records: 7 encounters, 6 clinical events, 6 observations, 5 medications,
  18 PDFs, 1 pathology report, 1 referral, and no imaging.
- Validation: passed; all 18 PDF checksums and asset registrations passed.
- Import: passed; repeat import returned `unchanged`.
- Investigation replay: completed with the deterministic-rules engine; 8
  verified findings and 82 verified anchors. The evaluator reported discovery
  failure with 1/6 required-source coverage, which is recorded as an engine
  baseline limitation rather than hidden or corrected in the dataset.

The dataset preserves the uncertainty between routing, acknowledgment, patient
discussion, and completed follow-up.

## Investigation generalization audit — 2026-10-22

The clinical dataset is unchanged. The following is a measured development-cohort replay.

### Clinical timeline and encounters

| Encounter | Started | Department |
| --- | --- | --- |
| ENC-003-01 | 2026-01-10T09:00:00+03:00 | Primary Care |
| ENC-003-02 | 2026-01-24T09:00:00+03:00 | Gastroenterology |
| ENC-003-03 | 2026-01-31T09:00:00+03:00 | Endoscopy |
| ENC-003-04 | 2026-02-02T09:00:00+03:00 | Pathology |
| ENC-003-05 | 2026-02-08T09:00:00+03:00 | Primary Care |
| ENC-003-06 | 2026-03-05T09:00:00+03:00 | Primary Care |
| ENC-003-07 | 2026-04-14T09:00:00+03:00 | Gastroenterology |

### Laboratory and medication inventory

Laboratory values are source observations; fasting/random context remains in original records.

| Analyte | Measurements | Recorded values |
| --- | ---: | --- |
| Hemoglobin | 2 | 10.8 g/dL (LAB-003-01-01); 11.4 g/dL (LAB-003-02-01) |
| MCV | 2 | 78 fL (LAB-003-01-02); 81 fL (LAB-003-02-02) |
| Ferritin | 2 | 9 ng/mL (LAB-003-01-03); 14 ng/mL (LAB-003-02-03) |

| Medication record | Medication | Status | Ordered |
| --- | --- | --- | --- |
| MED-003-01 | Ferrous sulfate 325 mg | active | 2026-01-10T09:00:00+03:00 |
| MED-003-02 | Ferrous sulfate 325 mg | active | 2026-02-08T09:00:00+03:00 |
| MED-003-03 | Omeprazole 20 mg | active | 2026-01-10T09:00:00+03:00 |
| MED-003-04 | Omeprazole 20 mg | active | 2026-01-24T09:00:00+03:00 |
| MED-003-05 | Bismuth subsalicylate | active | 2026-02-08T09:00:00+03:00 |

### Diagnostic reports and PDF documents

| Diagnostic report | Type | Issued | Source document |
| --- | --- | --- | --- |
| RPT-003-01 | pathology | 2026-02-02T11:00:00+03:00 | None |

| Document | Title | Event time |
| --- | --- | --- |
| DOC-003-01 | Initial anemia consultation | 2026-01-10T09:40:00+03:00 |
| DOC-003-02 | Baseline complete blood count | 2026-01-10T09:40:00+03:00 |
| DOC-003-03 | Gastroenterology consultation | 2026-01-24T09:40:00+03:00 |
| DOC-003-04 | Upper endoscopy order | 2026-01-24T09:40:00+03:00 |
| DOC-003-05 | Upper endoscopy procedure note | 2026-01-31T09:40:00+03:00 |
| DOC-003-06 | Specimen collection record | 2026-01-31T09:40:00+03:00 |
| DOC-003-07 | Gastric biopsy pathology report | 2026-02-02T09:40:00+03:00 |
| DOC-003-08 | Pathology result routing record | 2026-02-02T09:40:00+03:00 |
| DOC-003-09 | Result management work queue | 2026-02-02T09:40:00+03:00 |
| DOC-003-10 | Primary care follow-up | 2026-02-08T09:40:00+03:00 |
| DOC-003-11 | Gastroenterology follow-up referral | 2026-02-08T09:40:00+03:00 |
| DOC-003-12 | Routine follow-up without pathology discussion | 2026-03-05T09:40:00+03:00 |
| DOC-003-13 | Referral scheduling record | 2026-03-05T09:40:00+03:00 |
| DOC-003-14 | Delayed gastroenterology review | 2026-04-14T09:40:00+03:00 |
| DOC-003-15 | Follow-up instructions | 2026-04-14T09:40:00+03:00 |
| DOC-003-16 | Follow-up blood count | 2026-04-14T09:40:00+03:00 |
| DOC-003-17 | Iron medication reconciliation | 2026-02-08T09:40:00+03:00 |
| DOC-003-18 | Surveillance referral letter | 2026-04-14T09:40:00+03:00 |

PDF storage keys, byte sizes and hashes are enumerated in the unchanged case manifest; all registered assets passed canonical validation.

### Evidence source map and source-level diagnosis

| Required source | Retrieved | Cited | Verified | Failure stage |
| --- | --- | --- | --- | --- |
| DOC-003-05 | True | False | False | consolidation_or_linking |
| DOC-003-07 | True | False | False | consolidation_or_linking |
| DOC-003-08 | True | False | False | consolidation_or_linking |
| DOC-003-09 | True | False | False | consolidation_or_linking |
| DOC-003-10 | True | False | False | consolidation_or_linking |
| DOC-003-14 | True | True | True | none |

The detailed baseline diagnosis and intended challenge are documented in [failure analysis](../evaluation/CASE-002-to-006-investigation-failure-analysis.md). Search-hit retrieval is not proof of original-document review or private reasoning.

### Measured baseline and post-improvement results

| Metric | Before | After |
| --- | --- | --- |
| Verified findings | 8 | 10 |
| Required source coverage | 1/6 | 1/6 |
| Frozen discovery grade | failure | failure |
| Tools | 37 | 39 |
| Unsupported verified findings (independent replay) | 0 | 0 |

### Validation commands and limitations

Executed from repository root:

```text
uv run --project apps/api --locked python scripts/audit_investigations.py --output docs/evaluation/artifacts/generalization --phase before
uv run --project apps/api --locked python scripts/audit_investigations.py --output docs/evaluation/artifacts/generalization --phase after
```

Both runs validated the canonical schema, manifest and registered asset checksums, imported all six patients into a new migrated temporary database, checked required-source ownership, and reverified published findings. All 138 frozen input hashes remained unchanged.

Primary and secondary semantic discovery are not separately graded by the existing scorer, which requires a timeline contradiction even for non-timeline findings. Increased source coverage is not clinical discovery success. Pathology workflow and diagnostic hypothesis comparison remain unimplemented; medication exposure and causal conclusions remain unresolved. No expert clinical review or held-out evaluation is claimed.

See [improvement report](../evaluation/CASE-002-to-006-investigation-improvement-report.md) for complete regression checks and remaining limitations.
