# Skill: Radiology Reports

## Purpose
Create credible synthetic imaging study metadata and radiologist-style reports linked to explicitly illustrative imagery.

## Required metadata
`study_id`, `patient_id`, `encounter_id`, `modality`, body region, order time, acquisition time, report time, interpreting role, report version/status, linked image asset IDs.

## Report sections
Exam, indication, technique, comparison, findings, impression, limitations (when applicable). Use medically cautious language and avoid unsupported definitive findings.

## Workflow
1. Define why imaging was ordered and what time it was available.
2. Build report from canonical study finding and link it to source study IDs.
3. Generate readable PDF and optionally a schematic illustration according to `imaging-generation.md`.
4. Keep any linked illustration explicitly marked as educational/synthetic and separate from diagnostic image claims.
5. Validate report claims do not exceed what synthetic image depicts, and all dates match study metadata.

## Gate
No authentic patient DICOM, institutional marks, or fake radiologist identity. Synthetic visual assets are not evidence of real pathology.
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
