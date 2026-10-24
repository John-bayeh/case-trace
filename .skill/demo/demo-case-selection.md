# Demo Case Selection

## Purpose
Select a single flagship case whose discovery is easy to understand and difficult to dismiss. Default: `CASE-001`, an intentional **timeline contradiction**, optimized for wow factor plus evidence credibility.

## Inputs
Synthetic case manifest, dataset version, record count, event timestamps/time zones, original document assets, evaluator-only answer key, agent access controls.

## Selection gates
- **Completeness:** encounters, clinical notes, medication history, labs, at least one relevant report/document where applicable, and functioning asset URLs.
- **Discoverability:** the contradiction is not stated explicitly in the main patient summary; the agent must connect at least two independently retrieved records.
- **Evidence:** at least two stable record IDs/source spans support the mismatch; apparent disagreement survives an explicit time-zone/time-precision check.
- **Clinical coherence:** no accidental inconsistency contaminates the mystery; medically plausible narrative reviewed for educational plausibility, not clinical safety certification.
- **Demonstrability:** clear starting question, visible progress milestones, and a compelling before/after narrative.
- **Determinism:** same case seed and retrieval paths repeatedly surface the same sources.

## Manifest shape (adapt names to authoritative schema)
```yaml
case_id: CASE-001
dataset_version: synthetic-v1
seed_id: casetrace-demo-001
scenario: timeline-contradiction
allowed_patient_id: <synthetic-patient-id>
expected_evidence_ids: [<source-id-a>, <source-id-b>]
asset_checksum_manifest: <path>
answer_key_access: evaluator-only
```
This is illustrative, not a replacement for `case-schema.md`.

## Procedure
1. Verify manifest and checksums; record exact version in run metadata.
2. Select the synthetic patient by stable ID; confirm search returns a single unambiguous match.
3. Run a **blind agent rehearsal**, with answer key inaccessible to all retrieval tools.
4. As evaluator, compare resulting finding and citations to the answer key in a separate validation step.
5. Reject if answer is only obtained through a leaked summary, unsourced model inference, or manually inserted UI state.
6. Freeze the selected dataset version before demo day.

## Do not
Choose a case because its headline sounds dramatic while assets are missing. Do not change dates merely to make the contradiction more obvious during the live run.

## Definition of done
Selection manifest is versioned, every source ID resolves, the core contradiction is reproducible, and an alternate backup case is documented if CASE-001 becomes unusable.
