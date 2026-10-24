# Contradiction Detection Skill

## Purpose
Find candidate discrepancies among chronology, medications, tests, notes, and reported clinical status; prioritize source-verifiable conflicts without claiming malpractice or diagnosis.

## Candidate shape
`contradiction_id`, `type`, `claim_a`, `claim_b`, `evidence_ids_a[]`, `evidence_ids_b[]`, `temporal_relation`, `severity_for_review`, `confidence`, `alternative_explanations[]`, `verification_status`, `review_questions[]`.

## Types
- `temporal_order`: result references an event that apparently occurs later.
- `clinical_note_vs_structured`: note says a test was negative while laboratory data differs.
- `medication_state`: medication described as stopped/active/administered inconsistently.
- `followup_gap`: explicitly ordered follow-up has no identifiable completion within available data (a *possible gap*, not proof of missed care).
- `cross_encounter`: repeated histories/discharge documents disagree about a meaningful event.
- `source_metadata`: authoring, ingestion, or service dates diverge.

## Workflow
1. Start with deterministic cross-field and interval comparisons.
2. Generate candidate pairs with concrete source references.
3. Exclude ordinary non-conflicts: different measurement times, different units, documented correction, planned vs completed orders, and contextual changes.
4. Retrieve original pages/rows for each side and inspect source revisions.
5. Seek benign explanations: transcription, timezones, retrospective entry, wrong encounter, specimen rerun, order status.
6. Rank verified high-impact inconsistencies for review; leave weak signals explicitly tentative.
7. Return no finding when evidence does not support one.

## Demo contract
CASE-001 should uncover the seeded chronology issue only via accessible records. A similar negative-control case should *not* trigger the scripted “wow” finding. Never hardcode case IDs, phrases, or conclusion text into detector logic.

## Tests / done
Test true contradiction, changed diagnosis over time, late note entry, same-day ambiguity, unit conversion, conflicting orders vs administrations, and absence of record. Every flagged conflict cites at least two specific source anchors or explains precisely which anchor is missing.
