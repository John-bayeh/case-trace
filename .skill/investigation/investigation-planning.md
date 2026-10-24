# Investigation Planning Skill

## Purpose / trigger
Convert a clinical-history question into a reproducible, bounded sequence of retrievals and checks before reasoning. Invoke at the start of every run and after materially new evidence changes priorities.

## Inputs
`patient_id`, goal, authorized tool inventory, record coverage summary if available, maximum tool calls, token/compute budget, optional time window. Do not preload the synthetic answer key.

## Output
`PlanTask[]`: `task_id`, `goal`, `tool_or_analysis_step`, `parameters`, `dependencies`, `priority`, `reason`, `status`, `expected_evidence_types`, `stop_condition`; plus overall missing-data/coverage risks.

## Workflow
1. Scope patient, objective, allowed modalities, and source access permissions.
2. Establish a minimal retrieval plan: demographics/encounter index, then relevant notes/labs/medications/imaging/referrals.
3. Form testable questions with neutral wording (e.g., “Do note dates align with lab collection and medication start dates?”).
4. Order by expected information gain; fetch indexes before expensive PDFs/images.
5. Reserve budget for contradiction verification and a counterevidence search.
6. Replan only when a trigger occurs: missing encounter, divergent timestamp, material contradiction, or inaccessible source.

## Rules
- Plan discovery, not a desired diagnosis or prewritten plot twist.
- Keep tasks idempotent and independent where possible; avoid duplicate tool calls.
- Set scope and stop criteria, e.g., maximum 25 tool calls in a demo run (configurable, not hardcoded).
- Do not mention `ground_truth` or call evaluator-only APIs.
- Failed retrievals become visible skipped/blocked tasks, not silent assumptions.

## Example
`find_encounters(patient_id)` → `get_lab_results(patient_id, encounter_ids)` → `get_medication_history(patient_id)` → `get_documents(patient_id)` → `compare event/authoring times` → `verify flagged sources`.

## Test / done
Unit tests prove a plan has bounded tool calls, valid dependencies, allowed scope, and a dedicated verification stage. Planning never reveals hidden CASE-001 answer data.
