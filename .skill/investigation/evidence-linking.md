# Evidence Linking and Citation Verification Skill

## Purpose
Make every substantial investigative claim open the exact originating hospital record, with the correct context highlighted in the UI.

## Citation anchor
Use stable `evidence_id`; resolve to `source_type`, `source_record_id`, `document_id?`, `encounter_id?`, `version`, and one of `field_path`, `page_index + region`, `image_id + region`, or `note_span` (character offsets/text quote). Include a short literal excerpt when permitted and content integrity fingerprint if available.

## Workflow
1. Extract material assertions from each candidate finding/report section.
2. Attach anchors for facts and conflicting statements, with separate links for each side of a contradiction.
3. Resolve every anchor against the stored source version; confirm correct patient and source.
4. Validate numeric values, units, dates, and quoted words match original records.
5. Check that highlights work in patient chart, lab view, medication table, scan/PDF viewer, and imaging report where applicable.
6. If an anchor is broken, demote claim to unverified and block publication as a verified finding.

## Citation semantics
Distinguish primary hospital data from later copies, narrative summaries, and agent interpretations. Multiple notes copying the same report are not independent confirmation. Keep amendments visible and link to the specific version quoted.

## Testing / done
Deep links resolve to correct patient/record and highlighted field; stale version, nonexistent page, mismatched value, and wrong-patient citation fail validation. Citation completeness is 100% for published factual findings.
