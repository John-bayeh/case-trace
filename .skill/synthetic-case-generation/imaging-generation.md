# Skill: Imaging Generation

## Purpose
Produce visually coherent **illustrative** synthetic assets for the hospital UI while preserving clear simulation status and correct study links.

## Input / output
Input: study ID, modality, body region, clinical context, target dimensions, rendering brief. Output: PNG/WebP or synthetic DICOM *only if implemented and validated*, metadata manifest, preview thumbnail, and SHA-256.

## Workflow
1. Prefer diagrammatic/illustrative synthetic X-ray/CT/MRI-style imagery, never actual patient images.
2. Generate with a clearly visible `SYNTHETIC — NOT FOR CLINICAL USE` overlay/watermark, including thumbnails.
3. Make body region, laterality, and modality labels agree with study metadata and report.
4. Store original + thumbnail; ensure image paths resolve from simulated hospital document endpoints.
5. Hash every output and register in image manifest with generation method and study ID.
6. Verify with an image-open step that the asset is legible and watermark cannot be confused for real clinical imaging.

## Acceptance
- Image opens in patient record and investigation evidence panel.
- Viewer never labels illustrative asset as diagnostic raw image.
- Imaging lookup returns valid authorized URLs/IDs, not unrestricted filesystem locations.

## Forbidden behavior
Do not scrape medical images with unknown licensing or use real patient scans. Do not claim generated image's pixels confirm a diagnosis.
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
