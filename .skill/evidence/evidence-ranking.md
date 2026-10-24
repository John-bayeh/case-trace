# Evidence Ranking Skill

## Purpose
Prioritize records for investigator attention while keeping **ranking separate from veracity and diagnostic certainty**. Relevant evidence can still be wrong; low-ranked evidence can still refute a hypothesis.

## Inputs
Candidate evidence, question/hypothesis, provenance quality, time precision, directness, version status, source dependencies and contradictory evidence.

## Transparent ranking policy
Evaluate ordinal dimensions rather than inventing a medically validated probability:
- **Directness:** direct structured measurement or contemporaneous signed statement vs copied/retrospective narrative vs model inference.
- **Relevance:** direct bearing on the precise claim, mechanism or contradictory timestamp.
- **Temporal fitness:** known appropriate event time, precision and ordering relative to disputed event.
- **Provenance quality:** immutable source version, verified anchor, signed/amended status, traceable processing.
- **Independence:** original independent observations vs repeated/copy-forward statements.
- **Materiality:** whether it can change the investigation conclusion, including refuting evidence.

Prefer configurable rule-based sort tuples with documented weights/tie breakers. If a score is needed, label it **review priority score**, explain its scale and factors, and do not treat it as a probability of truth or clinical risk.

## Workflow
1. Define the investigation question and candidate set.
2. Deduplicate by underlying source/observation lineage while retaining every view reference.
3. Compute explainable dimension ratings (e.g. high/medium/low/unknown) with machine-readable reasons.
4. Rank both supporting and refuting evidence; guarantee material counterevidence inclusion even when low scoring.
5. Group by issue and source dependency; never give copied notes multiple votes.
6. Present sorted results with provenance completeness indicators and human-review affordances.
7. Log scoring policy version and inputs to reproduce ordering.

## Edge cases
- A late signed amendment may correct an error; don't automatically prioritize older or newer notes.
- A direct result with uncertain patient/sample attribution must be flagged and may be invalid for the patient.
- A normalized test value must show original unit and conversion provenance.
- Clinical significance is not an absolute function of numeric abnormality; do not invent thresholds without supplied reference intervals and context.

## Tests and definition of done
- Same inputs and policy version produce same order.
- Copy-forward duplicates do not falsely increase evidentiary strength.
- Missing provenance is visible and penalized/flagged, never fabricated.
- Contradictory high-materiality records remain discoverable.
- UI explains *why ranked*, not *why proven*.
