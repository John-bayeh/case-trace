# CASE-004 Generation Report

Status: structurally valid and imported into the isolated validation database.

- Generator: `scripts/generate_cases003_006.py`
- Records: 6 encounters, 6 clinical events, 24 observations, 5 medications,
  18 PDFs, 5 diagnostic reports, 1 referral, and no imaging.
- Validation: passed; all 18 PDF checksums and asset registrations passed.
- Import: passed; repeat import returned `unchanged`.
- Investigation replay: completed with the deterministic-rules engine; 5
  verified findings and 40 verified anchors. The evaluator reported discovery
  failure with 1/3 required-source coverage. The case remains structurally
  valid and the result is preserved as an engine baseline.

The monitor finding challenges an anxiety-only explanation without asserting a
definitive alternative diagnosis.

## Investigation generalization audit — 2026-10-22

The clinical dataset is unchanged. The following is a measured development-cohort replay.

### Clinical timeline and encounters

| Encounter | Started | Department |
| --- | --- | --- |
| ENC-004-01 | 2026-01-08T09:00:00+03:00 | Internal Medicine |
| ENC-004-02 | 2026-01-29T09:00:00+03:00 | Internal Medicine |
| ENC-004-03 | 2026-02-12T09:00:00+03:00 | Cardiology |
| ENC-004-04 | 2026-03-05T09:00:00+03:00 | Internal Medicine |
| ENC-004-05 | 2026-04-16T09:00:00+03:00 | Internal Medicine |
| ENC-004-06 | 2026-05-21T09:00:00+03:00 | Internal Medicine |

### Laboratory and medication inventory

Laboratory values are source observations; fasting/random context remains in original records.

| Analyte | Measurements | Recorded values |
| --- | ---: | --- |
| TSH | 8 | 2.1 mIU/L (LAB-004-01-01); 2.1 mIU/L (LAB-004-02-01); 2.1 mIU/L (LAB-004-03-01); 2.1 mIU/L (LAB-004-04-01); 2.1 mIU/L (LAB-004-05-01); 2.1 mIU/L (LAB-004-06-01); 2.1 mIU/L (LAB-004-07-01); 2.1 mIU/L (LAB-004-08-01) |
| Hemoglobin | 8 | 13.8 g/dL (LAB-004-01-02); 13.8 g/dL (LAB-004-02-02); 13.8 g/dL (LAB-004-03-02); 13.8 g/dL (LAB-004-04-02); 13.8 g/dL (LAB-004-05-02); 13.8 g/dL (LAB-004-06-02); 13.8 g/dL (LAB-004-07-02); 13.8 g/dL (LAB-004-08-02) |
| Potassium | 8 | 4.3 mmol/L (LAB-004-01-03); 4.3 mmol/L (LAB-004-02-03); 4.3 mmol/L (LAB-004-03-03); 4.3 mmol/L (LAB-004-04-03); 4.3 mmol/L (LAB-004-05-03); 4.3 mmol/L (LAB-004-06-03); 4.3 mmol/L (LAB-004-07-03); 4.3 mmol/L (LAB-004-08-03) |

| Medication record | Medication | Status | Ordered |
| --- | --- | --- | --- |
| MED-004-01 | Propranolol 10 mg | active | 2026-01-08T09:00:00+03:00 |
| MED-004-02 | Propranolol 10 mg | active | 2026-01-29T09:00:00+03:00 |
| MED-004-03 | Propranolol 10 mg | held | 2026-02-12T09:00:00+03:00 |
| MED-004-04 | Propranolol 10 mg | active | 2026-03-05T09:00:00+03:00 |
| MED-004-05 | Propranolol 10 mg | active | 2026-04-16T09:00:00+03:00 |

### Diagnostic reports and PDF documents

| Diagnostic report | Type | Issued | Source document |
| --- | --- | --- | --- |
| RPT-004-01 | laboratory | 2026-01-08T11:00:00+03:00 | None |
| RPT-004-02 | laboratory | 2026-01-29T11:00:00+03:00 | None |
| RPT-004-03 | laboratory | 2026-02-12T11:00:00+03:00 | None |
| RPT-004-04 | laboratory | 2026-03-05T11:00:00+03:00 | None |
| RPT-004-05 | laboratory | 2026-04-16T11:00:00+03:00 | None |

| Document | Title | Event time |
| --- | --- | --- |
| DOC-004-01 | The Diagnosis That Explained Too Little record 1 | 2026-01-08T09:40:00+03:00 |
| DOC-004-02 | The Diagnosis That Explained Too Little record 2 | 2026-01-29T09:40:00+03:00 |
| DOC-004-03 | The Diagnosis That Explained Too Little record 3 | 2026-02-12T09:40:00+03:00 |
| DOC-004-04 | The Diagnosis That Explained Too Little record 4 | 2026-03-05T09:40:00+03:00 |
| DOC-004-05 | The Diagnosis That Explained Too Little record 5 | 2026-04-16T09:40:00+03:00 |
| DOC-004-06 | The Diagnosis That Explained Too Little record 6 | 2026-05-21T09:40:00+03:00 |
| DOC-004-07 | The Diagnosis That Explained Too Little record 7 | 2026-01-08T09:40:00+03:00 |
| DOC-004-08 | The Diagnosis That Explained Too Little record 8 | 2026-01-29T09:40:00+03:00 |
| DOC-004-09 | The Diagnosis That Explained Too Little record 9 | 2026-02-12T09:40:00+03:00 |
| DOC-004-10 | The Diagnosis That Explained Too Little record 10 | 2026-03-05T09:40:00+03:00 |
| DOC-004-11 | The Diagnosis That Explained Too Little record 11 | 2026-04-16T09:40:00+03:00 |
| DOC-004-12 | The Diagnosis That Explained Too Little record 12 | 2026-05-21T09:40:00+03:00 |
| DOC-004-13 | The Diagnosis That Explained Too Little record 13 | 2026-01-08T09:40:00+03:00 |
| DOC-004-14 | The Diagnosis That Explained Too Little record 14 | 2026-01-29T09:40:00+03:00 |
| DOC-004-15 | The Diagnosis That Explained Too Little record 15 | 2026-02-12T09:40:00+03:00 |
| DOC-004-16 | The Diagnosis That Explained Too Little record 16 | 2026-03-05T09:40:00+03:00 |
| DOC-004-17 | The Diagnosis That Explained Too Little record 17 | 2026-04-16T09:40:00+03:00 |
| DOC-004-18 | The Diagnosis That Explained Too Little record 18 | 2026-05-21T09:40:00+03:00 |

PDF storage keys, byte sizes and hashes are enumerated in the unchanged case manifest; all registered assets passed canonical validation.

### Evidence source map and source-level diagnosis

| Required source | Retrieved | Cited | Verified | Failure stage |
| --- | --- | --- | --- | --- |
| DOC-004-05 | True | True | True | none |
| DOC-004-08 | True | False | False | consolidation_or_linking |
| DOC-004-10 | True | False | False | consolidation_or_linking |

The detailed baseline diagnosis and intended challenge are documented in [failure analysis](../evaluation/CASE-002-to-006-investigation-failure-analysis.md). Search-hit retrieval is not proof of original-document review or private reasoning.

### Measured baseline and post-improvement results

| Metric | Before | After |
| --- | --- | --- |
| Verified findings | 5 | 6 |
| Required source coverage | 1/3 | 1/3 |
| Frozen discovery grade | failure | failure |
| Tools | 37 | 37 |
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
