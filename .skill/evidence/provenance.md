# Source Provenance Skill

## Purpose and trigger
Use while designing ingestion, evidence stores, source previews, document versioning and audit logging. Maintain a reliable chain from investigation observations to original hospital records.

## Provenance model
For each source maintain: tenant/hospital, patient, source system, resource type + primary key, encounter ID if applicable, source version/amendment ID, media type, content hash (when original bytes exist), received/retrieved timestamp, documented/clinical-effective timestamp, actor/tool call ID, and access scope. Store sensitive identifiers only where required and protect them.

For each evidence excerpt maintain: `evidence_id`, source-version foreign key, anchor (JSON path, page + text span, normalized character offsets, image region/series identifier), original value and unit, extracted value, extraction method (`structured` / `parser` / `model`), extraction version, and uncertainty. If OCR/extraction fails, mark unavailable; don't reconstruct missing characters as fact.

## Clock semantics
- `event_at`: real-world event time *as claimed by source* (e.g. specimen collected, medication administered).
- `authored_at`: clinical author date; `entered_at`: system-record entry; `signed_at`: signature; `amended_at`: correction.
- `retrieved_at`: the tool fetched the record; never substitute for clinical event time.
- Retain original timezone/offset and date-only precision; compare in UTC only when both instants are determinable.
- Flag uncertain/partial times, unknown local offsets, and contradictions between timestamps.

## Workflow
1. Validate authenticated authorization for patient and investigation before data leaves hospital adapter.
2. Collect typed records via documented hospital tools; retain raw payload or immutable content-addressed artifact when permitted.
3. Compute hash for bytes; for structured records use stable version identifier and deterministic serialization only if defined by project contract.
4. Generate immutable provenance reference and evidence excerpt anchor; link to tool-call/audit ID.
5. Add derivation edges for normalizations, merges, text extraction and interpretation. Mark derived material **not** as original source.
6. On corrected record create new version + supersession edge; keep prior evidence traceable and mark stale anchors for review.
7. Verify resolution from report to source version and exact excerpt.

## Never
- Trust a filename, screenshot, model summary or generated PDF as proof of the underlying record without matching source metadata.
- Mutate stored source observations during temporal cleanup or case-story refinement.
- Infer an event date from PDF creation time, upload time or UI display order.
- Leak other patients through source IDs, deep links, or error text.

## Tests and acceptance
- Hash mismatch triggers integrity failure and review, not transparent fallback.
- Source amended after investigation causes a version warning and explicit re-evaluation path.
- Repeated fetches of same source/version deduplicate without removing separate legitimate observations.
- Anchor resolution fails closed for unauthorized viewer, deleted artifact, different patient and unknown version.
- Exact source lineage is recoverable from every reported key finding.

## Stack alignment

Persist provenance and citation validation atomically with the corresponding finding/event through the controlled persistence service. Preserve source IDs, versions, hashes, anchors and distinct UTC time semantics; retries must not duplicate logical evidence/finding links. Use the [portable SQLite conventions](../../docs/development-stack.md) rather than engine-specific UUID/JSON/time assumptions.
