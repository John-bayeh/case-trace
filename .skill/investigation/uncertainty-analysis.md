# Uncertainty Analysis Skill

## Purpose
Communicate what evidence establishes, what is inferred, and what cannot be decided from available synthetic records.

## Uncertainty dimensions
`source_reliability`, `temporal_precision`, `record_completeness`, `interpretation_ambiguity`, `alternative_explanations`, `verification_coverage`.

## Rules
- Use descriptive confidence (`high|moderate|low|insufficient`) with an explicit rationale; do not fabricate calibrated numerical probabilities.
- Separate *verified discrepancy* from *cause of discrepancy*, *patient impact*, and *recommended clinical action*.
- An absent result in retrieved records is not proof no result exists elsewhere.
- A contradictory note may reflect an addendum, late-entry, copied text, timezone, or lab status difference.
- If original source cannot be inspected, retain finding as unverified.

## Workflow
1. Collect corroborating and opposing evidence and identify dependencies.
2. Evaluate precision (date-only vs exact time) and coverage limits.
3. Record missing encounters/documents, failed tool calls, and uncertain OCR.
4. Assign confidence separately for each claim, contradiction and hypothesis.
5. Write a concise, actionable verification question; avoid prescriptive medical advice.
6. Downgrade confidence if material counterevidence remains unresolved.

## Output example
“Two records disagree on the recorded test timing (high confidence: both verified); whether the discrepancy reflects a late note entry remains unresolved (insufficient evidence).”

## Testing / done
Cases with partial histories, OCR errors, cross-source disagreements, and corrected notes correctly expose uncertainty; no false precision or unsupported certainty.
