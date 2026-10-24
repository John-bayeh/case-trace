# Hypothesis Testing Skill

## Purpose
Resolve competing explanations through planned source retrieval and explicit support/refutation logic.

## Assessment shape
`hypothesis_id`, `test_id`, `question`, `evidence_ids_examined[]`, `tool_call_ids[]`, `supports[]`, `weakens[]`, `unresolved[]`, `verdict` (`supported|weakened|inconclusive`), `reasoning_summary`, `limitations[]`.

## Workflow
1. Define test criteria *before* calling additional tools.
2. Retrieve targeted record metadata, original notes, result status, medication administration logs, and document revisions as appropriate.
3. Contrast expected observations under each hypothesis with what records actually show.
4. Include a deliberate counterevidence search: corrections, superseded reports, alternative time sources, later documentation.
5. Update assessments using evidence references, not freeform impressions.
6. Stop if budgets are exhausted or further tests cannot discriminate; report remaining uncertainty.

## Strict separation
A source note’s assessment is a **documented clinical opinion**, not established fact. A hypothesis assessment is a **CASETRACE inference**, not a diagnosis. Ground truth is evaluator-only and may be used for scoring after a completed run, never for runtime inference.

## Tests / done
One fixture where extra metadata resolves contradiction; one where ambiguous dates remain inconclusive; one with falsifying evidence. Assertions cover tool trace, evidence links, and no forced winning hypothesis.
