---
name: synthetic-case-generation
description: 'Generate a complete, reproducible, multimodal fictional hospital record for CASETRACE''s evidence-based timeline investigations. Apply this skill before all specialized generation skills. Use for: Creating or revising CASE-001–CASE-010, seeding a simulated hospital environment, or adjusting a case''s narrative, attachments, or expected contradictions.'
---

# Skill: Synthetic Case Generation

## Purpose
Generate a complete, reproducible, multimodal fictional hospital record for CASETRACE's evidence-based timeline investigations. Apply this skill before all specialized generation skills.

## When to use
Creating or revising CASE-001–CASE-010, seeding a simulated hospital environment, or adjusting a case's narrative, attachments, or expected contradictions.

## Inputs
- Case ID, learning/demo objective, clinical setting, fictional patient profile, time range.
- A *private* ground-truth specification of the key finding and exact supporting/contradicting record IDs.
- Existing schema/API contracts and seed/generation parameters.

## Outputs
Complete folder, manifest, structured records, documents/images, private answer key, validation summary, and repeatable generation command.

## Workflow
1. Read `case-schema.md`, `hospital-api.md`, `agent-tools.md` and existing manifests.
2. Define **immutable canonical events** and their timestamps before writing narrative documents.
3. Design the investigation as a minimum three-source reasoning chain: earlier objective fact → later incompatible claim → corroborating evidence.
4. Generate encounters, labs, orders/administrations, imaging, referrals, and notes from canonical events using subskills.
5. Render documents and illustrative images with manifests, checksums, and access-controlled paths.
6. Seed via the same ingestion pipeline the simulated hospital uses; never grant investigation agents raw filesystem access.
7. Validate schema, time, medical plausibility, provenance, cross-media links, and blind replay.

## Agent rules
- Never invent data on retrieval; materialize artifacts during the generation step.
- Do not solve the case in a document title, filenames, exposed annotation, or seeded chart summary.
- Use explicit case version and seed so demo resets are deterministic.

## Deliverable checklist
- Every resource has stable IDs, provenance, event time and recorded time.
- Hidden answer key identifies expected claim, decisive evidence IDs, benign alternative explanations, and uncertainty.
- At least one neutral/distractor record is included; not every unusual finding proves the mystery.
## Non-negotiable constraints
- All patients, professionals, facilities, accession IDs, and identifiers are fictional. Never copy real patient records or use actual identifying data.
- Mark every generated document and image **SYNTHETIC — NOT FOR CLINICAL USE** in visible metadata or footer. Avoid realistic institutional logos/signatures implying authenticity.
- Use `case-schema.md` as the source of truth for field names; use `hospital-api.md` for exposed resources and `agent-tools.md` for investigator access. If these are unavailable, produce an explicit mapping rather than silently inventing incompatible fields.
- Record source timestamps with ISO 8601 plus timezone, including event time, recorded time, result time, and amendment time as applicable. Never conflate these.
- Ground truth is private test-only data, not exposed through the simulated hospital API or retrieval tools. No leakage via filenames, document titles, metadata, UI summaries, or API payloads.
- An intentionally incorrect clinical assertion must remain plausibly documented as an assertion; do not silently alter underlying objective facts to manufacture a contradiction.
- These artifacts support a simulated investigation demo, never diagnosis or treatment decisions.

## Common case envelope
Use stable IDs: `CASE-001`, `PAT-CASE-001`, `ENC-001-01`, `LAB-001-01`, `MED-001-01`, `DOC-001-01`, `IMG-001-01`. Never reuse identifiers across records. Cross-reference by ID rather than copying facts into uncontrolled prose.

Proposed on-disk organization (adapt to the authoritative schema):
```text
cases/CASE-001/
  manifest.json
  timeline/events.json
  encounters/encounters.json
  labs/lab-results.json
  medications/medication-events.json
  imaging/studies.json
  documents/metadata.json
  documents/rendered/*.pdf
  images/synthetic/*
  ground-truth/answer-key.json  # inaccessible to investigation runtime
  validation/report.json
```

## Required validation for every generated record
1. Validate against authoritative JSON schemas and unique/cross-reference IDs.
2. Validate chronological relationships and distinguish missing data from negative findings.
3. Reconcile narrative claims with labs, medication administrations, and imaging metadata; register deliberate discrepancies in *private* ground truth.
4. Verify renderable files exist, their checksums match manifests, and redaction/synthetic markings are present.
5. Run a blind agent replay against public hospital endpoints; expected clue is discoverable only via tool-accessible evidence, not ground-truth files.

## Definition of done
A deterministic generation command recreates the artifact, all validations pass, and the case is investigative without being solved by a single obvious note.

## Finalized stack

Follow [development stack and SQLite operations](../../docs/development-stack.md) for setup or persistence work: pnpm for Next.js, uv for FastAPI, SQLite + aiosqlite + SQLAlchemy 2.x + Alembic. Commands remain planned until manifests/scripts exist. Preserve tool boundaries, source provenance and evaluator isolation; never hold a database transaction across inference or external waits.
