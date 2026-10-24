# Patient Search — Skill

## Purpose
Locate a synthetic patient **without false-positive identity merges**, then establish a scoped `patient_id` for subsequent tools.

## Inputs
Permitted search criteria: exact stable ID, synthetic medical-record number, name tokens, date of birth, or case-specific identifier as allowed by `hospital-api.md`; `tenant_id`/facility scope; authorized actor; optional pagination.

## Procedure
1. Normalize whitespace and case for text matching; preserve original input for audit.
2. Prefer exact ID/MRN over fuzzy name; do not silently match on one weak attribute.
3. Apply tenant/facility and actor scope before returning matches.
4. Return minimal demographics needed for disambiguation, stable IDs, match method and paginated counts.
5. Require explicit selection when multiple similar matches exist. Do not auto-merge records.
6. Check subsequent retrievals against the selected patient ID, not against a UI-supplied name.

## Example result shape (illustrative)
```json
{"patients":[{"patient_id":"P-001","display_name":"Synthetic Patient A","dob":"1981-06-12","mrn":"SYN-001","facility_id":"HOSP-DEMO","match_type":"exact_mrn"}],"next_cursor":null}
```

## Forbidden behavior
Do not return full histories in search results, leak cross-tenant matches, use fabricated matches, or report that two same-name records are identical without an explicit verified identifier.

## Tests / done
Test exact match, case-insensitive search, pagination, no matches, ambiguous matches, disallowed scope, hostile query strings, and deterministic ordering. A search result must lead to a stable scoped patient record.
