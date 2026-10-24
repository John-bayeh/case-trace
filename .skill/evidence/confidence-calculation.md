# Confidence and Uncertainty Skill

## Purpose
Communicate strength and limitations of CASETRACE investigative conclusions without inventing numerical medical certainty. Confidence applies to **specific propositions**, not the entire patient or diagnosis.

## Default policy: qualitative confidence
Use explainable classes until held-out data and formal calibration exist:
- **Strongly supported:** multiple relevant, independently sourced records with verified links and no material unaddressed counterevidence.
- **Provisionally supported:** at least one direct verified source but notable limitations or unresolved alternative interpretations.
- **Inconclusive:** evidence incomplete, contradictory, dependent or insufficiently precise to discriminate explanations.
- **Contradicted:** reliable direct evidence materially opposes the specific proposition.

These labels describe **evidentiary support** under the available record set; they are not validated probabilities of diagnosis, safety, or causality. Unknown data completeness should cap interpretive certainty.

## Required output attributes
`proposition_id`, `support_level`, `supports[]`, `refutes[]`, `missing_information[]`, `source_dependency_groups[]`, `assessment_rationale`, `policy_version`, `review_status`. Adapt the names to the existing project contract. Retain uncertainty from OCR, timestamp precision, source conflicts, missing records, and inference steps.

## Assessment procedure
1. Specify narrowly worded proposition and whether it is factual observation, comparative chronology or hypothesis.
2. Verify all cited anchors and source versions; label unverifiable sources.
3. Evaluate independence, directness, relevance, completeness, temporality and material contradictory records.
4. Generate support level with a short deterministic explanation and explicit missing data.
5. For comparisons, explain whether timestamps describe the same kind of event and the effect of uncertainty intervals.
6. Keep competing hypotheses side-by-side when records don't distinguish them.
7. Require clinician review for clinically consequential conclusions; include non-diagnostic and synthetic-data disclaimers where appropriate.

## Numerical scoring (only if truly needed)
Do **not** display `92% confidence`, clinical risk probabilities, or invented posteriors by default. A numeric score is acceptable only when (a) defined prediction target and labeled evaluation dataset exist, (b) dependence/leakage are controlled, (c) held-out calibration and error analysis were performed, (d) score is documented and versioned, and (e) UI explicitly states what the number means and does not mean. A ranking score is not a confidence probability.

## Avoid these errors
- Counting copied notes as multiple independent sources.
- Treating missing contrary evidence as confirmation.
- Calling a temporal sequence proof of causality.
- Equating signed note with infallible report or model agreement with clinical validation.
- Allowing changing source versions or missing anchors to silently retain previous confidence.

## Acceptance tests
- Removing sole direct evidence lowers support level or renders it inconclusive.
- Adding reliable counterevidence changes displayed rationale and flags conflict.
- Two identical copied notes do not elevate support.
- Temporal uncertainty prevents unjustified exact ordering.
- No unsupported percentage can reach the report or API UI payload.

## Definition of done
Every claim includes interpretable evidentiary support, counterevidence, and unresolved limitations; review by a human remains possible through exact citations.
