# Conflicting Evidence Resolution Skill

## Purpose
Identify and surface genuine discordance among observations without automatically deleting, rewriting or choosing a convenient narrative. Core CASE-001 objective: a credible **timeline contradiction** discoverable from independent hospital records.

## Conflict categories
- **Temporal:** event ordering, specimen collection vs result entry, order vs administration, reported symptom onset vs encounter date.
- **Clinical assertion:** notes disagree about symptoms, procedures, allergies, medication adherence or measurements.
- **Identity/provenance:** mismatched patient, encounter, accession, document version or signing clinician.
- **Measurement:** inconsistent values, units, reference ranges, methodology or specimen provenance.
- **Documentation:** amended, back-entered, copy-forward, retrospective or date-only records.

## Structured conflict object (illustrative)
```json
{
  "conflict_id": "cf-001",
  "kind": "temporal",
  "claim_a": {"evidence_id": "ev-017", "time_field": "collected_at"},
  "claim_b": {"evidence_id": "ev-025", "time_field": "administered_at"},
  "relationship": "apparent_order_mismatch",
  "status": "unresolved",
  "alternative_explanations": [
    "Time was entered retrospectively",
    "One timestamp refers to documentation rather than event occurrence"
  ],
  "review_action": "Inspect original lab accession and medication administration record"
}
```

## Investigation procedure
1. Choose the exact propositions being compared and link both to immutable evidence references.
2. Normalize only compatible units/timezones; maintain original values and precision.
3. Check patient, encounter, version, status, specimen, document creation vs event times, and duplicate lineage.
4. Express observed contradiction as a falsifiable comparison (e.g. `lab.collected_at < med.administered_at`) with actual source timestamps.
5. Generate plausible alternative interpretations and retrieve further **authorized** corroborating records.
6. Record evidence *for and against* each explanation; distinguish refutation from absent evidence.
7. Status may be `unresolved`, `explained_documentation`, `corroborated_discrepancy`, or `review_required` per project schema; do not claim validated clinical causation.
8. Surface balanced conflict card: both sources, dates, field semantics, context, alternatives, follow-up checks and outstanding limitations.

## Guardrails
- A contradictory chart entry is not proof that a clinician erred or that a specific diagnosis is correct.
- An absence from available records is not proof the event did not happen; qualify completeness.
- No silent preference for the most recent/signed/source with higher priority.
- Do not alter source material to agree with synthetic hidden case ground truth.
- Generated test fixtures may assert expected conflicts, but those labels may be used only in an isolated evaluator, never runtime agent context.

## Tests and definition of done
- Temporal mismatch across two encounters is flagged with both precise source anchors.
- Backdated entry is distinguished from actual clinical-event time where metadata permits.
- Same-event duplicates don't create false conflicts.
- Date-only or ambiguous timezone evidence yields an uncertainty warning rather than false precision.
- Conflict remains independently reviewable even if agent favors one hypothesis.
