# CASE-005 Generation Report

Status: structurally valid and imported into the isolated validation database.

- Generator: `scripts/generate_cases003_006.py`
- Records: 7 encounters, 7 clinical events, 28 observations, 6 medications,
  19 PDFs, 5 diagnostic reports, 1 referral, and no imaging.
- Validation: passed; all 19 PDF checksums and asset registrations passed.
- Import: passed; repeat import returned `unchanged`.
- Investigation replay: completed with the deterministic-rules engine; 6
  verified findings and 48 verified anchors. The evaluator reported discovery
  failure with 1/3 required-source coverage. The case remains structurally
  valid and the result is preserved as an engine baseline.

The data distinguishes hold instructions, order status, reconciliation,
patient report, and actual exposure uncertainty.

## Investigation generalization audit — 2026-10-22

The clinical dataset is unchanged. The following is a measured development-cohort replay.

### Clinical timeline and encounters

| Encounter | Started | Department |
| --- | --- | --- |
| ENC-005-01 | 2026-01-08T09:00:00+03:00 | Internal Medicine |
| ENC-005-02 | 2026-01-29T09:00:00+03:00 | Internal Medicine |
| ENC-005-03 | 2026-02-12T09:00:00+03:00 | Cardiology |
| ENC-005-04 | 2026-03-05T09:00:00+03:00 | Internal Medicine |
| ENC-005-05 | 2026-04-16T09:00:00+03:00 | Internal Medicine |
| ENC-005-06 | 2026-05-21T09:00:00+03:00 | Internal Medicine |
| ENC-005-07 | 2026-06-18T09:00:00+03:00 | Internal Medicine |

### Laboratory and medication inventory

Laboratory values are source observations; fasting/random context remains in original records.

| Analyte | Measurements | Recorded values |
| --- | ---: | --- |
| Creatinine | 7 | 0.9 mg/dL (LAB-005-01-01); 0.9 mg/dL (LAB-005-02-01); 0.9 mg/dL (LAB-005-03-01); 0.9 mg/dL (LAB-005-04-01); 0.9 mg/dL (LAB-005-05-01); 0.9 mg/dL (LAB-005-06-01); 0.9 mg/dL (LAB-005-07-01) |
| Hemoglobin | 7 | 13.1 g/dL (LAB-005-01-02); 13.1 g/dL (LAB-005-02-02); 13.1 g/dL (LAB-005-03-02); 13.1 g/dL (LAB-005-04-02); 13.1 g/dL (LAB-005-05-02); 13.1 g/dL (LAB-005-06-02); 13.1 g/dL (LAB-005-07-02) |
| Platelets | 7 | 221 10^9/L (LAB-005-01-03); 221 10^9/L (LAB-005-02-03); 221 10^9/L (LAB-005-03-03); 221 10^9/L (LAB-005-04-03); 221 10^9/L (LAB-005-05-03); 221 10^9/L (LAB-005-06-03); 221 10^9/L (LAB-005-07-03) |
| INR | 7 | 1.1 ratio (LAB-005-01-04); 1.1 ratio (LAB-005-02-04); 1.1 ratio (LAB-005-03-04); 1.1 ratio (LAB-005-04-04); 1.1 ratio (LAB-005-05-04); 1.1 ratio (LAB-005-06-04); 1.1 ratio (LAB-005-07-04) |

| Medication record | Medication | Status | Ordered |
| --- | --- | --- | --- |
| MED-005-01 | Apixaban 5 mg | active | 2026-01-08T09:00:00+03:00 |
| MED-005-02 | Apixaban 5 mg | active | 2026-01-29T09:00:00+03:00 |
| MED-005-03 | Apixaban 5 mg | held | 2026-02-12T09:00:00+03:00 |
| MED-005-04 | Apixaban 5 mg | active | 2026-03-05T09:00:00+03:00 |
| MED-005-05 | Apixaban 5 mg | active | 2026-04-16T09:00:00+03:00 |
| MED-005-06 | Apixaban 5 mg | held | 2026-05-21T09:00:00+03:00 |

### Diagnostic reports and PDF documents

| Diagnostic report | Type | Issued | Source document |
| --- | --- | --- | --- |
| RPT-005-01 | laboratory | 2026-01-08T11:00:00+03:00 | None |
| RPT-005-02 | laboratory | 2026-01-29T11:00:00+03:00 | None |
| RPT-005-03 | laboratory | 2026-02-12T11:00:00+03:00 | None |
| RPT-005-04 | laboratory | 2026-03-05T11:00:00+03:00 | None |
| RPT-005-05 | laboratory | 2026-04-16T11:00:00+03:00 | None |

| Document | Title | Event time |
| --- | --- | --- |
| DOC-005-01 | The Missing Days of Anticoagulation record 1 | 2026-01-08T09:40:00+03:00 |
| DOC-005-02 | The Missing Days of Anticoagulation record 2 | 2026-01-29T09:40:00+03:00 |
| DOC-005-03 | The Missing Days of Anticoagulation record 3 | 2026-02-12T09:40:00+03:00 |
| DOC-005-04 | The Missing Days of Anticoagulation record 4 | 2026-03-05T09:40:00+03:00 |
| DOC-005-05 | The Missing Days of Anticoagulation record 5 | 2026-04-16T09:40:00+03:00 |
| DOC-005-06 | The Missing Days of Anticoagulation record 6 | 2026-05-21T09:40:00+03:00 |
| DOC-005-07 | The Missing Days of Anticoagulation record 7 | 2026-06-18T09:40:00+03:00 |
| DOC-005-08 | The Missing Days of Anticoagulation record 8 | 2026-01-08T09:40:00+03:00 |
| DOC-005-09 | The Missing Days of Anticoagulation record 9 | 2026-01-29T09:40:00+03:00 |
| DOC-005-10 | The Missing Days of Anticoagulation record 10 | 2026-02-12T09:40:00+03:00 |
| DOC-005-11 | The Missing Days of Anticoagulation record 11 | 2026-03-05T09:40:00+03:00 |
| DOC-005-12 | The Missing Days of Anticoagulation record 12 | 2026-04-16T09:40:00+03:00 |
| DOC-005-13 | The Missing Days of Anticoagulation record 13 | 2026-05-21T09:40:00+03:00 |
| DOC-005-14 | The Missing Days of Anticoagulation record 14 | 2026-06-18T09:40:00+03:00 |
| DOC-005-15 | The Missing Days of Anticoagulation record 15 | 2026-01-08T09:40:00+03:00 |
| DOC-005-16 | The Missing Days of Anticoagulation record 16 | 2026-01-29T09:40:00+03:00 |
| DOC-005-17 | The Missing Days of Anticoagulation record 17 | 2026-02-12T09:40:00+03:00 |
| DOC-005-18 | The Missing Days of Anticoagulation record 18 | 2026-03-05T09:40:00+03:00 |
| DOC-005-19 | The Missing Days of Anticoagulation record 19 | 2026-04-16T09:40:00+03:00 |

PDF storage keys, byte sizes and hashes are enumerated in the unchanged case manifest; all registered assets passed canonical validation.

### Evidence source map and source-level diagnosis

| Required source | Retrieved | Cited | Verified | Failure stage |
| --- | --- | --- | --- | --- |
| DOC-005-05 | True | True | True | none |
| DOC-005-08 | True | False | False | consolidation_or_linking |
| DOC-005-10 | True | False | False | consolidation_or_linking |

The detailed baseline diagnosis and intended challenge are documented in [failure analysis](../evaluation/CASE-002-to-006-investigation-failure-analysis.md). Search-hit retrieval is not proof of original-document review or private reasoning.

### Measured baseline and post-improvement results

| Metric | Before | After |
| --- | --- | --- |
| Verified findings | 6 | 8 |
| Required source coverage | 1/3 | 1/3 |
| Frozen discovery grade | failure | failure |
| Tools | 39 | 39 |
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
