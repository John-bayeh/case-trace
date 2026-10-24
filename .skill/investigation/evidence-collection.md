# Evidence Collection Skill

## Purpose
Retrieve and register verifiable records from the simulated hospital without contaminating originals or inventing missing facts.

## Inputs / outputs
Input: plan tasks and permitted hospital tools. Output: `EvidenceItem[]`, tool execution log, retrieval coverage, and error/missing-source log.

## EvidenceItem minimum
`evidence_id`, `patient_id`, `source_type`, `source_record_id`, `encounter_id?`, `document_id?`, `locator` (field path / page + bounding box / image annotation), `content_excerpt?`, `normalized_value?`, `unit?`, `effective_at?`, `recorded_at?`, `source_version?`, `sha256?`, `retrieved_at`, `tool_call_id`, `reliability_notes[]`. Adapt names to project schemas while preserving semantics.

## Workflow
1. Validate patient scope and tool parameters.
2. Call only declared functions in `agent-tools.md` / `hospital-api.md`.
3. Persist tool name, validated arguments, execution ID, duration, success/failure, and returned source identifiers.
4. Register evidence with canonical IDs; keep source-native text and any normalization side-by-side.
5. For scans, distinguish OCR/transcription from raw document image; link to page/region and flag uncertain transcription.
6. Deduplicate by stable source ID/version; don't discard contradictory versions or amendments.
7. Record explicit `not_found`, `unavailable`, `permission_denied`, or `parse_failed` statuses.

## Provenance rules
A summary, model output, or previously generated CASETRACE report is **not an independent primary source**. Preserve authorship, timestamps, accession/order IDs, specimen times, note addenda, document revisions, and original units. Never mutate source content to simplify demo narration.

## Forbidden
No fabricated values or quotations. No silent patient switch, hidden answer-key lookup, or scraping outside the simulated authorized system. Never claim that absent records prove an event did not happen.

## Testing / done
Mock tool success, timeout, malformed response, amended note, duplicated document, and wrong-patient payload. Assert correct provenance, scoped filtering, error reporting, and evidence deduplication with amendments retained.

## Stack alignment

SQLite writes go through the controlled application persistence service. Commit retrieval/audit start, release sessions during external work, and persist typed results/evidence with stable retry keys in a separate short transaction. See [SQLite operations](../../docs/development-stack.md); concurrent agents must not share sessions or overwrite a newer investigation version.
