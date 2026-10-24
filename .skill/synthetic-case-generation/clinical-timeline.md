# Skill: Clinical Timeline

## Purpose
Create a temporally coherent longitudinal record with deliberately discoverable **source-level contradiction**, not arbitrary timestamp errors.

## Inputs / outputs
Input: canonical case events, encounter windows, intended mystery. Output: versioned `timeline/events.json` plus date-indexed references to every source resource.

## Event contract
Each event should record `event_id`, `case_id`, `patient_id`, `encounter_id` (optional), `event_type`, `occurred_at`, `documented_at`, `source_resource_ids`, `status`, and `timezone`. Preserve `resulted_at`, `signed_at`, `amended_at` separately when needed. Use only fields allowed by the schema or documented mapping.

## Workflow
1. Construct a **private** chronological truth table of encounters, symptoms, tests, orders, actual administrations, results, and follow-ups.
2. Create at least 3 encounters spanning a plausible clinical timeframe; distribute key observations among separate resource types.
3. Choose a source statement that conflicts with objective events (e.g., a later note says an abnormal result was reviewed before it was actually reported).
4. Record precisely which claim conflicts with which timestamps and what remains uncertain.
5. Generate notes and documents **after** canonical events exist.
6. Validate that test collection precedes result time, signing may occur later, and no amended record is silently backdated.

## Forbidden patterns
- Making timestamps inconsistent solely because of timezone formatting.
- Assuming ordering equals administration, or ordering equals result availability.
- Introducing secret facts known only from ground truth and unavailable in the chart.

## Tests
Assert chronological invariants, link coverage, nonduplicate timestamps/IDs where uniqueness is required, and a replayable three-source inference chain.
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
