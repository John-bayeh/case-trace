# Phase 2 source provenance boundary

## Phase 2.3 medication reconciliation

The existing medication_reconciliation envelope now supports independently
reconstructed medication-specific assertions. ClinicalClaim origin additionally
permits copied_list and administration (documented administration, not inferred
ingestion). Identity uses explicit ingredient/strength/formulation/route and
does not infer synonyms. Source event, authored, ordered and intended start/end
times remain distinct. Explicit ISO planned dates are retained as qualifiers;
unknown relative applicability stays unknown. The verifier regenerates the
complete consolidated candidate and canonical claim from independently fetched
originals. Actual ingestion, causal injury and definitive diagnosis remain
unsupported. Cross-specialist laboratory association questions remain unresolved.

## Phase 2.2 typed relationship evidence

Candidates/findings may include an optional `relationship` envelope composed of
the existing ClinicalClaim assertions, evidence roles, named temporal ordering
and unresolved questions. The additive `clinical_relationship` rule resolves
hospital originals, reconstructs assertions and independently regenerates narrow
record-level propositions. Candidate prose cannot establish verification.
Unsupported ingestion/causal/diagnostic intents are rejected; broader clinical
interpretation remains inconclusive. Existing anchor fields and fingerprints
remain unchanged. See [relationship architecture](architecture/clinical-relationship-reasoning.md).

## Refactor 06 additive reasoning contract

`INVESTIGATION_REASONING=structured` opts into bounded source-claim extraction
and comparison; `legacy` remains the default. Both workflow strategies retain
the existing tool and verifier boundaries. Narrative anchors now retain complete
source statements. Optional `char_start` / `char_end` offsets are paired,
zero-based, end-exclusive Unicode character offsets into the unmodified field;
when supplied, its slice must equal `quote`. Old field-only anchors remain valid.
No PDF page or coordinates are inferred.

Internal clinical claims preserve source identity/version/hash, subject,
attribution, polarity, certainty, episode and date precision. Comparison verifies
documented propositions, never true clinical onset or causality. Unknown episodes,
approximate times and missing follow-up evidence stay explicitly uncertain.
Unsupported rule families remain inconclusive. This adds no persistence tables.

## Phase 3 claim anchors and verification

An anchor identifies source_type, source_id, source_version, source_hash,
encounter_id, field, expected value and optional exact quote. Types follow the
hospital resource vocabulary. Source hashes cover canonical hospital DTO JSON
(sorted keys, compact separators, UTF-8); the hospital service supplies versions.
Quotes require exact substring matching in the specified string field. Values
and timestamps must equal the original DTO field, with instant comparisons in
UTC. Missing/changed/foreign-patient sources fail closed. Registered document
assets are integrity checked before accepting document evidence.

A finding carries claim_kind, rule, anchors, alternatives and limitations.
Implemented deterministic rules verify exact field observations, comparable lab
changes and explicit symptom-onset conflicts against earlier contemporaneous
clinical events. The onset parser is deliberately narrow and checks event and
documentation chronology; it does not establish a clinical cause or true onset.
`review_before_result` remains an accepted proposal rule but has no implemented
verification branch and therefore remains inconclusive. Its intended future
implementation must require exact source-ID mention and review language, compare
result availability and note authoring time, and test delayed-entry controls.
See [Refactor 01 compatibility decision C-08](refactoring/04-contract-compatibility.md).
Free-form interpretations/hypotheses remain unresolved even with valid citations.
Verification statuses are verified/rejected/inconclusive; finding statuses are
proposed/verified/rejected/unresolved. Every check is persisted with the finding.
No numerical confidence is generated: strong means all deterministic checks pass,
limited means valid anchors with unresolved interpretation, insufficient means
missing or invalid evidence. These are evidence labels, not medical probabilities.

The source-lineage section below originated in Phase 2. The implemented Phase 3
anchor and verification contract is summarized above and in
[Phase 3 decisions](phase-3-decisions.md); it is no longer an unimplemented gate.

Each imported source preserves its canonical ID, patient/encounter links, dataset
case/version, source system, source version, original clinical payload and named
timestamps. Internal UUIDs never replace source IDs in public DTOs. Document
versions retain text SHA-256 and optional registered asset FK. Assets retain
storage key, MIME, size, SHA-256 and an explicit synthetic label. A source-document
link must resolve within the same patient. No citation is invented for records
without a source document.

Canonical source files are maintenance inputs, never runtime endpoints. Only
allowlisted clinical fields enter the runtime database. Ground truth,
investigation targets, expected relationships, red-herring labels and scoring
metadata remain outside runtime DB/assets. Deployment must exclude raw cases and
evaluation directories, as in the existing Docker configuration. Local process
file permissions are an operator responsibility: API omission alone is not OS
isolation. Future agents may only use approved tools over hospital services.

## Longitudinal observation verification (generalization audit)

`record_series` is an additive candidate rule using existing medication_change
and laboratory_change types. It compares source-specific recorded reference
bounds across compatible analytes and differing medication order snapshots
across encounters. Laboratory batches contain up to three measurements;
medication batches contain up to four orders, with one overlapping record.
The existing twenty-anchor limit and execution budgets remain unchanged.
Only original source representations may contribute evidence. Relevant linked
source documents are retrieved through the laboratory/medication tool scopes.
The independent verifier regenerates the proposition from resolved records and
requires the complete generated anchor set. Candidate prose is replaced with
the canonical observation. Different medication states are not automatically
contradictions; repeated source-range abnormalities are not diagnoses.
Free-form follow-up, causal and diagnostic interpretations stay inconclusive.
# Phase 2.4 result workflow evidence

Phase 2.5 diagnostic_comparison reuses the bounded source search manifest for
working-assessment versus objective-interpretation comparisons. Independently
repeated category search and original resolution protect against omitted opposing
interpretations. Reconstruction checks the entire comparison, factual assertions,
certainty, chronology, patient/encounter links and exact source anchors. Empty,
over-limit, changed or unavailable evidence remains unverified. Supported record
relationships can include an inconclusive or non-challenged provisional verdict;
verified does not mean a diagnosis is established. Hypothesis.comparison is emitted
only from a verified comparison; incoming provider comparison fields are cleared.
Source-interpreted findings are distinct from measurements and final diagnoses.
Generic context never supplies an invented diagnosis, causal link or later date.

The optional relationship.result_workflow carries result_id, attribution,
search (complete, categories, document_limit, appointment_coverage and original
source/version/hash manifest), and eleven lifecycle stages. Each stage has a
documented/partial/unknown/conflicting state and exact source observations with
named event_time_field, timestamps and literal narrative dates. Metadata/narrative
date conflicts are retained; narrative dates do not become invented instants.
Unknown means unestablished, not that an action did not happen. The result rule
independently repeats all four category searches and source resolution before
reconstructing the complete envelope, anchors and canonical record-level claim.
Changed, omitted, foreign or stale evidence fails closed. Incomplete search is
inconclusive. Later completed referral/review and patient notification evidence
constrain absence claims. This adds no proof of negligence, progression or diagnosis.
