# Imaging Retrieval — Skill

## Purpose
Provide safe access to synthetic imaging studies, their **radiologist reports**, and associated illustrative image assets.

## Inputs
Scoped patient; optional encounter, modality, anatomical region, time range, status; `study_id` or `image_id` for detail.

## Procedure
1. Retrieve study metadata: study ID, accession, modality, body region, `ordered_at`, `performed_at`, `reported_at`, status and linked encounter.
2. Keep interpreted radiology report text distinct from pixels/images and any generated illustrative asset.
3. Return image metadata and access handles from the artifact service; use content-type checks and expiring URLs or secured proxy reads.
4. Record whether an image is `synthetic_illustration`, simulation, or another synthetic type. Do not misrepresent an AI-generated visual as a real diagnostic image.
5. Preserve series, image orientation and ordering only when the fixture contains them; missing properties stay unknown.
6. Link image, report and finding citations using stable study/report IDs; treat interpretations as authored report statements, not model-confirmed medical truth.

## Example
```json
{"study_id":"IMG-STUDY-004","patient_id":"P-001","modality":"XR","performed_at":"2026-04-12T10:30:00+03:00","report_id":"RAD-004","assets":[{"asset_id":"IMG-004A","kind":"synthetic_illustration","mime_type":"image/png"}]}
```

## Forbidden behavior
Do not claim diagnostic fidelity for generated images, infer clinical findings from thumbnail appearance, expose filesystem paths or missing protected assets, or fabricate a study when no record exists.

## Tests / done
Check modality filters, report-image links, rendition security, nonimage content rejection, missing/invalid image, access scope and image labeling in UI.
