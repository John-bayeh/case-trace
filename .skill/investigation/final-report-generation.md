# Final Investigation Report Generation Skill

## Purpose
Turn a verified investigation into a clinician-reviewable narrative and structured report, without overclaiming or hiding limitations.

## Report schema (map to frontend/backend contract)
`report_id`, `investigation_id`, `patient_id`, `schema_version`, `generated_at`, `status`, `question`, `executive_summary`, `key_findings[]`, `timeline[]`, `contradictions[]`, `hypotheses[]`, `evidence_registry[]`, `missing_information[]`, `confidence_rationale`, `review_questions[]`, `methodology`, `limitations`, `audit_trail_ref`, `synthetic_data_notice`.

## Required report sections
1. Investigation objective and patient/case identity (synthetic demo labels).
2. Headline finding with *verification status*; no sensational diagnosis or blame.
3. Reconstructed chronology, linking critical events.
4. Contradictory source statements side-by-side, each with citation anchors.
5. Alternative explanations and tests, including counterevidence.
6. Conclusions: observed facts vs inferred hypotheses vs unresolved issues.
7. Recommended **human review questions**, not unsupervised treatment directives.
8. Data limitations, provenance, tool/verification audit, generation timestamp.

## Workflow
1. Consume immutable verified investigation snapshot; do not independently reinterpret raw text beyond the evidence registry.
2. Build structured JSON first and validate with Pydantic.
3. Validate every assertion and citation with `evidence-linking.md`.
4. Ensure summaries do not overstate confidence relative to underlying findings.
5. Render UI and optional downloadable document from the *same* canonical report object.
6. Persist schema version, input snapshot hash, report version, and tool-event history for reproducibility.
7. If verification fails, expose `draft_unverified` with issues instead of publishing `verified`.

## Language guidance
Prefer “Records conflict about…” / “May warrant chart reconciliation” over “The clinician missed…” / “CASETRACE diagnosed…”. State when there is insufficient evidence to infer cause or clinical consequences.

## Tests / done
Golden fixtures assert deterministic structure, accurate date/unit quoting, two-way contradiction citations, accessible original source links, counterevidence and limitations, correct status. The PDF/HTML rendering must match report JSON and display a visible synthetic-data banner.
