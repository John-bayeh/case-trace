# Skill: Clinical Notes

## Purpose
Generate human-readable synthetic clinical narratives that reflect individual encounter perspectives and preserve documentary provenance.

## Output types
H&P, ED assessment, progress note, discharge summary, nurse note, follow-up note, and addendum (only when clinically appropriate).

## Required metadata
`document_id`, `patient_id`, `encounter_id`, `author_role`, fictional author, `created_at`, `signed_at`, note type, status, version, source event links, and optional supersedes ID.

## Workflow
1. Select encounter and note author's knowledge cutoff (`authored_at`).
2. Pull only evidence available by that time; avoid retroactive omniscience.
3. Use concise sections: chief concern, history, relevant observations, assessment, plan, follow-up.
4. Distinguish patient-reported symptoms, clinician interpretation, and objectively measured values.
5. If this is the intentionally contradictory document, encode a plausible claim in a note while keeping original objective records unchanged.
6. Store text, metadata, and printable rendition sharing one document ID.

## Quality gate
- Note aligns with its author's timeframe and role.
- Signed and amended versions are explicitly differentiated.
- No unreferenced exact lab value or medication administration is fabricated.
- No explicit answer or mention of a 'planted clue' appears in runtime content.
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
