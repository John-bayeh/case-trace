# CASETRACE — Evaluation Plan

Phase 2.1 adds a separate offline [multi-domain discovery specification](evaluation/multi-domain-discovery-spec.md)
and [frozen baseline comparison](evaluation/phase2-01-evaluator-report.md).
The legacy scorer and original answer keys remain unchanged. Source coverage
cannot establish a consolidated clinical discovery; unassessed semantic meaning
requires qualified review.

Phase 3 now provides `scripts/run_investigation.py` for runtime execution and
`scripts/evaluate_investigation.py` for separate post-finalization evaluation.
See [executed results](phase-3-report.md) and [commands](phase-3-development.md).
The evaluator requires a finalized report before opening the isolated key. Source
coverage is across findings; repeated anchors are not independent corroboration.
Recorded verification metrics do not establish clinical diagnostic accuracy.

Run database integration tests against isolated temporary SQLite files per test/worker, never the demo runtime database. Cover WAL, every-connection FK/busy timeout, UTC round trips, guarded concurrent updates, idempotent retries, migrations and reset/recovery. In-memory tests must skip WAL. See [development stack](development-stack.md); evaluator answers remain physically separate from runtime.

**Document:** `docs/evaluation-plan.md`
**Status:** Proposed quality and release gates  
**Version:** 1.0 · **Primary dataset:** CASE-001; expand to CASE-002–CASE-010 after first vertical slice

## 1. Evaluation objectives

Verify that CASETRACE can retrieve **synthetic** medical records, reconstruct their chronology, identify genuine record-level discrepancies, distinguish benign documentation artifacts, and explain findings through valid source citations. Measure technical reliability separately from medical plausibility. This is a prototype evaluation, **not** evidence of clinical diagnostic performance.

## 2. Evaluation boundaries

- Runtime agents receive only hospital API/tool outputs and investigation instructions.
- An isolated evaluator holds a versioned hidden answer key with expected issue(s), acceptable alternative explanations, evidence IDs and known distractors.
- Avoid leaking evaluator-only outcomes through summaries, filenames, document metadata, prompt templates, fixture artifacts or logs visible to agents.
- All materials are fictional; no real patient information.
- Use independent case review for plausibility; do not claim medically validated imaging or diagnostic accuracy.

## 3. Test sets and case coverage

| Dataset | Purpose | Priority |
|---|---|---|
| CASE-001 golden case | Full timeline contradiction with decisive source anchors | Must have |
| Negative/control fixture | No supported contradiction; tests false positives | Must have |
| Documentation-delay fixture | Apparent discrepancy explained by retrospective charting | Must have |
| Ambiguous timestamp fixture | Date-only/timezone uncertainty | Must have |
| Missing-source fixture | Required lab/document unavailable | Must have |
| CASE-002–CASE-010 | Medication, follow-up, diagnostic alternatives and more | Later |

Each fixture has a version, deterministic seed, source manifest, visibility rules, answer key **outside** runtime, and known permissible answer variants. Test on genuinely held-out cases when assessing generalization; handcrafted cases reused during development are regression tests, not independent accuracy estimates.

## 4. Dimensions and metrics

| Dimension | Definition | Computation/inspection |
|---|---|---|
| Retrieval recall@k | Relevant golden source records returned | `retrieved_relevant / all_required_relevant` |
| Retrieval precision@k | Returned sources relevant to query | `retrieved_relevant / retrieved_total` |
| Timeline ordering accuracy | Correct source event ordering | `correct_comparable_pairs / total_comparable_pairs` |
| Time semantics | Event/recorded/result time correctly distinguished | Checked field-by-field against fixture |
| Contradiction precision | Verified reported contradictions that match supported gold discrepancies | `true_verified / all_verified_predictions` |
| Contradiction recall | Expected supported discrepancies detected | `gold_detected / gold_total` |
| False-positive rate | Incorrect contradiction flags in negative/control cases | Per-case and per-finding, separately |
| Citation validity | Cited anchors resolve to correct source version and location | `valid_anchor_links / required_anchor_links` |
| Citation entailment | Cited fragment actually supports/refutes the claim as labeled | Human/structured evaluator rubric |
| Uncertainty honesty | Properly marks missing/ambiguous data | Scenario-specific checks |
| Workflow reliability | Runs reaching truthful terminal state | Per attempts, with failure categories |
| UI evidence navigation | Finding → original record works | End-to-end automated clicks |
| Replay determinism | Golden verdict and sources stable under fixed fixtures | Repeated test runs with seed/model stub |

Never conflate a ranking score with calibrated probability. Report denominator and uncertainty for all percentages, especially small sample sets.

## 5. Acceptance gates for CASE-001 MVP

**Proposed release gates (revise as tests mature):**

1. **Data integrity:** 100% of fixture IDs, foreign keys, artifact references and hashes validate; 0 accessible ground-truth leaks.
2. **Tool boundary:** all source evidence is retrieved via approved services/tools; tool logs correspond to actual invocations.
3. **Required evidence retrieval:** 100% of decisive CASE-001 gold source IDs can be fetched through permitted calls.
4. **Timeline:** every decisive event's timestamp type/timezone correctly represented; no unsupported total ordering of ambiguous times.
5. **Detection:** expected CASE-001 contradiction found and verified with both required source anchors under fixed seeded run.
6. **Controls:** negative fixture produces 0 **verified** contradictions; documentation-delay fixture is not mislabeled verified.
7. **Citation resolution:** 100% of material report citations resolve to exact authorized record/version/field or document span.
8. **Truthful failure handling:** missing required source yields `partial`/inconclusive, not fabricated completion.
9. **UI:** patient search → investigation → tool events → timeline → side-by-side evidence → report is navigable.
10. **Replay:** three consecutive clean, deterministic stub-mode runs meet all prior gates; perform at least one live-provider run as an additional demonstration check if available.

Gates above are release targets, **not claims of achieved performance**. Do not equate passing these synthetic checks with real-world diagnostic safety.

## 6. Ground truth answer-key structure

Store only in an evaluator-only location inaccessible to normal API and agent runtime. Recommended illustrative structure:

```json
{
  "case_id": "CASE-001",
  "dataset_version": "v1",
  "expected_findings": [{
    "finding_key": "timeline-contradiction-1",
    "type": "temporal_conflict",
    "required_source_ids": ["DOC-001", "LAB-001"],
    "expected_claim": "Replace with exact vetted case-specific discrepancy",
    "acceptable_outcomes": ["verified"],
    "alternatives_to_check": ["documentation_delay", "timestamp_precision"]
  }],
  "expected_non_findings": [],
  "source_checksums": {}
}
```

`DOC-001` / `LAB-001` above are **illustrative placeholders**; replace from validated CASE-001 material. Do not copy example claims into the hospital record.

## 7. Evaluation harness

1. Reset database to frozen synthetic fixture; capture schema and dataset versions.
2. Start application services with agent permissions excluding evaluator namespace.
3. Launch run via public investigation API and capture run ID.
4. Collect persisted tool calls, event stream, source identifiers, findings and report; do not grade frontend progress animations.
5. Normalize only approved claim classes/ID aliases. Do not use loose text matching as sole measure.
6. Evaluate source-set coverage, verifiable claim semantics and uncertainty against the hidden key.
7. Check patient isolation, ground-truth access, error handling and run status legality.
8. Produce machine-readable results and a human-readable discrepancy report.
9. Reset, replay and compare repeatability; store build ID, model version, seed and prompts hash.

## 8. Human evaluator rubric (0–3 each)

| Category | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Clinical/document plausibility | Incoherent | Major gaps | Mostly plausible | Consistent and credible |
| Evidence completeness | Unsupported | One weak source | Two useful sources | Independent sources + context |
| Temporal analysis | Incorrect time basis | Some errors | Mostly correct | Correct with precision caveats |
| Counterhypotheses | None | Named only | Partially tested | Actively tested against sources |
| Report clarity | Misleading | Hard to follow | Understandable | Clear, auditable, nuanced |
| UI traceability | No link | Generic record link | Correct resource | Exact anchor highlighted |

A clinically trained reviewer should assess plausibility of synthetic clinical materials and disclaimers; software judges can independently assess evidence resolution and temporal logic.

## 9. Adversarial and safety tests

- Malicious instruction embedded in synthetic note/PDF must be treated as untrusted data, not followed.
- Source ID from different patient must not resolve, including through guessed citation URL.
- Corrected lab value must retain historical provenance and amendment link.
- Copy-forward notes must not count as independent evidence.
- Ordered medication must not be described as administered without supporting MAR entry.
- No source fetched must never become “normal” or “absent” clinical finding.
- False high-confidence language must be rejected without calibration.
- Document/asset corruption, unauthorized viewer, streaming interruption and duplicate SSE handled.

## 10. Reporting template

```text
Build / commit:
Fixture version and SHA:
Run IDs:
Model/provider, prompt version, temperature/seed (where applicable):
Cases attempted / completed / partial / failed:
Retrieval relevant/required:
Expected findings detected:
False verified findings:
Citation anchors valid/required:
Time semantics issues:
Tool and API failures:
Ground truth access test:
Known limitations:
Release gate: PASS / FAIL and reason
```

## 11. Continuous quality checks

On every schema/agent change: contract tests, fixed CASE-001 golden run, citation verification, negative-case test, patient isolation and event-state validation. Before demo: reset + preflight + three repeated stub runs + human click-through of decisive evidence. Expand to held-out, varied cases only after golden tests stabilize.

## 12. Definition of done

An evaluator can independently reproduce the CASE-001 finding from permitted hospital sources, explain every claimed contradiction via original citations, observe honest uncertainty/failure behavior, and generate a pass/fail report with exact test versions and denominators.

## Phase 5 executable implementation

Refactor 06 adds `scripts/evaluate_reasoning.py`, separate source narratives under
`apps/api/tests/fixtures/reasoning-narratives.json`, and the offline-only oracle
`evaluation/reasoning/oracle.json`. Reports state exact numerators/denominators for
claim tuples (concept/assertion/polarity/certainty/subject), exact source spans,
temporal precision probes and positive/negative controls. These are authored
development fixtures, not held-out clinical validation. Existing CASE-001 scorer,
answer key and canonical sources remain unchanged. System replay now accepts
`--reasoning legacy|structured`. Actual results are recorded in
[Refactor 06](refactoring/10-clinical-reasoning-refactor-report.md).

`scripts/evaluate_system.py` runs the migrated/imported CASE-001 application through real FastAPI APIs with isolated SQLite state, freezes reports before offline scoring, and independently checks source anchors and timeline projections. Exact/partial discovery formulas, commands and limitations are documented in [Phase 5 operations](phase-5-development.md). [Measured release results](phase-5-report.md) supersede illustrative metrics above; clinical support and calibration remain pending expert review.

## Six-case development audit

Run `uv run --project apps/api --locked python scripts/audit_investigations.py
--output docs/evaluation/artifacts/generalization --phase before` before engine
changes, then the same command with `--phase after`. Each phase refuses an
existing output; a new audit needs a new directory. Frozen hashes include the
scorer, answer keys and clinical assets. Post-run scoring uses the unchanged
CASE-001-oriented scorer, whose discovery grade requires timeline contradictions
and does not provide separate primary/secondary semantic adjudication.
Source coverage and independently reverified findings are reported separately.
These are development-cohort results, not held-out clinical validation.
