# Skill: Document Generation

## Purpose
Render consistent PDFs and optional scanned-style fictional documents from structured canonical records, preserving search and provenance.

## Supported artifacts
Lab result sheets, encounter summaries, prescriptions, referrals, progress notes, discharge letters, imaging reports.

## Workflow
1. Input structured resource IDs and text; generate nothing clinically new during rendering.
2. Use a reusable fictional hospital identity with distinct specimen/order IDs; do not mimic real hospital marks.
3. Embed visible `SYNTHETIC — NOT FOR CLINICAL USE` footer on each page.
4. Prefer selectable/searchable text PDFs. For scanned-style views, generate a raster overlay **and** retain OCR-independent source text and document metadata.
5. Record SHA-256, MIME type, page count, linked resource IDs, created-at, version, and storage location in manifest.
6. Validate that downloadable/viewable document data matches source records and that viewer deep-links resolve to document ID/page.

## Acceptance tests
- PDF renders across all pages, no clipping, no broken fonts or missing table rows.
- Filename and title are neutral, never disclose case answer.
- Visible synthetic notice remains legible in preview and print.
- Investigation citation links identify source ID and page; page-to-resource links survive export.
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
