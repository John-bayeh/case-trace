# CASE-006 Generation Report

Status: structurally valid and imported into the isolated validation database.

- Generator: `scripts/generate_cases003_006.py`
- Records: 7 encounters, 7 clinical events, 32 observations, 5 medications,
  18 PDFs, 5 laboratory reports, 1 referral, and no imaging.
- Validation: passed; all 18 PDF checksums and asset registrations passed.
- Import: passed; repeat import returned `unchanged`.
- Investigation replay: completed with the deterministic-rules engine; 7
  verified findings and 68 verified anchors. The evaluator reported discovery
  failure with 1/3 required-source coverage. The case remains structurally
  valid and the result is preserved as an engine baseline.

The longitudinal glucose and HbA1c pattern is presented as a screening and
follow-up concern, not as an automatic diabetes diagnosis.

## Investigation generalization audit — 2026-10-22

The clinical dataset is unchanged. The following is a measured development-cohort replay.

### Clinical timeline and encounters

| Encounter | Started | Department |
| --- | --- | --- |
| ENC-006-01 | 2026-01-08T09:00:00+03:00 | Internal Medicine |
| ENC-006-02 | 2026-01-29T09:00:00+03:00 | Internal Medicine |
| ENC-006-03 | 2026-02-12T09:00:00+03:00 | Cardiology |
| ENC-006-04 | 2026-03-05T09:00:00+03:00 | Internal Medicine |
| ENC-006-05 | 2026-04-16T09:00:00+03:00 | Internal Medicine |
| ENC-006-06 | 2026-05-21T09:00:00+03:00 | Internal Medicine |
| ENC-006-07 | 2026-06-18T09:00:00+03:00 | Internal Medicine |

### Laboratory and medication inventory

Laboratory values are source observations; fasting/random context remains in original records.

| Analyte | Measurements | Recorded values |
| --- | ---: | --- |
| Glucose | 8 | 112 mg/dL (LAB-006-01-01); 114 mg/dL (LAB-006-02-01); 116 mg/dL (LAB-006-03-01); 118 mg/dL (LAB-006-04-01); 120 mg/dL (LAB-006-05-01); 122 mg/dL (LAB-006-06-01); 124 mg/dL (LAB-006-07-01); 126 mg/dL (LAB-006-08-01) |
| HbA1c | 8 | 6.0 % (LAB-006-01-02); 8.0 % (LAB-006-02-02); 10.0 % (LAB-006-03-02); 12.0 % (LAB-006-04-02); 14.0 % (LAB-006-05-02); 16.0 % (LAB-006-06-02); 18.0 % (LAB-006-07-02); 20.0 % (LAB-006-08-02) |
| Creatinine | 8 | 0.9 mg/dL (LAB-006-01-03); 0.9 mg/dL (LAB-006-02-03); 0.9 mg/dL (LAB-006-03-03); 0.9 mg/dL (LAB-006-04-03); 0.9 mg/dL (LAB-006-05-03); 0.9 mg/dL (LAB-006-06-03); 0.9 mg/dL (LAB-006-07-03); 0.9 mg/dL (LAB-006-08-03) |
| Triglycerides | 8 | 182 mg/dL (LAB-006-01-04); 182 mg/dL (LAB-006-02-04); 182 mg/dL (LAB-006-03-04); 182 mg/dL (LAB-006-04-04); 182 mg/dL (LAB-006-05-04); 182 mg/dL (LAB-006-06-04); 182 mg/dL (LAB-006-07-04); 182 mg/dL (LAB-006-08-04) |

| Medication record | Medication | Status | Ordered |
| --- | --- | --- | --- |
| MED-006-01 | Metformin 500 mg | active | 2026-01-08T09:00:00+03:00 |
| MED-006-02 | Metformin 500 mg | active | 2026-01-29T09:00:00+03:00 |
| MED-006-03 | Metformin 500 mg | held | 2026-02-12T09:00:00+03:00 |
| MED-006-04 | Metformin 500 mg | active | 2026-03-05T09:00:00+03:00 |
| MED-006-05 | Metformin 500 mg | active | 2026-04-16T09:00:00+03:00 |

### Diagnostic reports and PDF documents

| Diagnostic report | Type | Issued | Source document |
| --- | --- | --- | --- |
| RPT-006-01 | laboratory | 2026-01-08T11:00:00+03:00 | None |
| RPT-006-02 | laboratory | 2026-01-29T11:00:00+03:00 | None |
| RPT-006-03 | laboratory | 2026-02-12T11:00:00+03:00 | None |
| RPT-006-04 | laboratory | 2026-03-05T11:00:00+03:00 | None |
| RPT-006-05 | laboratory | 2026-04-16T11:00:00+03:00 | None |

| Document | Title | Event time |
| --- | --- | --- |
| DOC-006-01 | The Pattern Hidden Across Routine Visits record 1 | 2026-01-08T09:40:00+03:00 |
| DOC-006-02 | The Pattern Hidden Across Routine Visits record 2 | 2026-01-29T09:40:00+03:00 |
| DOC-006-03 | The Pattern Hidden Across Routine Visits record 3 | 2026-02-12T09:40:00+03:00 |
| DOC-006-04 | The Pattern Hidden Across Routine Visits record 4 | 2026-03-05T09:40:00+03:00 |
| DOC-006-05 | The Pattern Hidden Across Routine Visits record 5 | 2026-04-16T09:40:00+03:00 |
| DOC-006-06 | The Pattern Hidden Across Routine Visits record 6 | 2026-05-21T09:40:00+03:00 |
| DOC-006-07 | The Pattern Hidden Across Routine Visits record 7 | 2026-06-18T09:40:00+03:00 |
| DOC-006-08 | The Pattern Hidden Across Routine Visits record 8 | 2026-01-08T09:40:00+03:00 |
| DOC-006-09 | The Pattern Hidden Across Routine Visits record 9 | 2026-01-29T09:40:00+03:00 |
| DOC-006-10 | The Pattern Hidden Across Routine Visits record 10 | 2026-02-12T09:40:00+03:00 |
| DOC-006-11 | The Pattern Hidden Across Routine Visits record 11 | 2026-03-05T09:40:00+03:00 |
| DOC-006-12 | The Pattern Hidden Across Routine Visits record 12 | 2026-04-16T09:40:00+03:00 |
| DOC-006-13 | The Pattern Hidden Across Routine Visits record 13 | 2026-05-21T09:40:00+03:00 |
| DOC-006-14 | The Pattern Hidden Across Routine Visits record 14 | 2026-06-18T09:40:00+03:00 |
| DOC-006-15 | The Pattern Hidden Across Routine Visits record 15 | 2026-01-08T09:40:00+03:00 |
| DOC-006-16 | The Pattern Hidden Across Routine Visits record 16 | 2026-01-29T09:40:00+03:00 |
| DOC-006-17 | The Pattern Hidden Across Routine Visits record 17 | 2026-02-12T09:40:00+03:00 |
| DOC-006-18 | The Pattern Hidden Across Routine Visits record 18 | 2026-03-05T09:40:00+03:00 |

PDF storage keys, byte sizes and hashes are enumerated in the unchanged case manifest; all registered assets passed canonical validation.

### Evidence source map and source-level diagnosis

| Required source | Retrieved | Cited | Verified | Failure stage |
| --- | --- | --- | --- | --- |
| DOC-006-05 | True | True | True | none |
| DOC-006-08 | True | True | True | none |
| DOC-006-10 | True | True | True | none |

The detailed baseline diagnosis and intended challenge are documented in [failure analysis](../evaluation/CASE-002-to-006-investigation-failure-analysis.md). Search-hit retrieval is not proof of original-document review or private reasoning.

### Measured baseline and post-improvement results

| Metric | Before | After |
| --- | --- | --- |
| Verified findings | 7 | 20 |
| Required source coverage | 1/3 | 3/3 |
| Frozen discovery grade | failure | failure |
| Tools | 37 | 45 |
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
