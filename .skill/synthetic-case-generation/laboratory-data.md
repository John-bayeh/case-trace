# Skill: Laboratory Data

## Purpose
Build clinically plausible structured, longitudinal lab orders and results that are traceable to specimen and encounter.

## Required fields
Order ID, panel/analyte ID, specimen ID, encounter, collection time, receipt time (if modeled), result time, units, reference interval, flag, status, performer, report document ID, amendment history.

## Workflow
1. Pick a bounded panel relevant to the case; prefer familiar analytes with conventional units.
2. Consult a verified, unit-specific reference source for medically consequential ranges; record the source and version in generator notes (not patient chart).
3. Define canonical numeric observations before rendering reports.
4. Preserve consistent units and avoid accidentally converting values inconsistently across notes and PDFs.
5. Include ordered-but-not-performed, pending, abnormal, and repeat values only when warranted by storyline.
6. Attach report PDFs to the same lab IDs and checksum each file.

## Test cases
- Reject result time preceding collection unless explicitly classified as imported/corrected data.
- Confirm abnormal flags match numeric value and reference range.
- Reconcile repeat result with baseline trend and note text.
- Distinguish missing specimen from negative test.

## Safety
No real laboratory identifiers or diagnostic instructions. Generated values are for simulation and must be reviewed for plausibility rather than presumed medically authoritative.
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
