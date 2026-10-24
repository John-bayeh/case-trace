# Hypothesis Generation Skill

## Purpose
Produce a small set of **testable explanations** for a verified discrepancy, not an unconstrained list of diagnoses.

## Inputs / outputs
Input: contradiction candidates, timeline, verified evidence, context and gaps. Output: `Hypothesis[]` with `hypothesis_id`, `statement`, `category`, `supporting_evidence_ids[]`, `contradicting_evidence_ids[]`, `discriminating_questions[]`, `requested_tools[]`, `assumptions[]`, `status`.

## Workflow
1. State the observation independently from its possible interpretation.
2. Propose 2–4 plausible explanations, including at least one mundane data-workflow cause when appropriate (late documentation, transcription, cross-encounter confusion).
3. Add an explicit `insufficient_information` option.
4. Make each hypothesis falsifiable: what exact record or timestamp would favor/refute it?
5. Prefer tools that resolve distinctions cheaply and deterministically.
6. Avoid diagnosis-level inference when case evidence concerns documentation only.

## Guardrails
Use cautious phrasing (“consistent with,” “could reflect”). Never assign fabricated likelihoods or cite model-generated commentary as independent corroboration. Avoid implying harm, fraud, negligence, or definitive diagnosis without sufficient records and clinician review.

## Tests / done
Given a contradiction, output includes competing hypotheses and discriminating checks; given insufficient context, outputs uncertainty instead of invented history. Explanations link back to evidence.
