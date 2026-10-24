# Claim-Level Citation Linking Skill

## Purpose
Ensure every clinically material claim and temporal comparison in a CASETRACE report links to the **exact original record location**, not just a general patient page.

## Data contract
Maintain typed many-to-many `claim_evidence_link` records: claim ID, evidence ID, role (`supports`, `refutes`, `context`, `unresolved`), proposition component, optional note, and link-validation status. Store anchors independently of view URLs; backend resolves authenticated navigation at access time.

Supported anchor examples (match actual sources):
- Structured field: record ID + version + JSON pointer; present label/value/unit.
- Clinical document: artifact ID + hash + page + text span/line offsets or selection geometry.
- Medication record: exact order, dispense or administration event plus status and time field.
- Image: study/series/image identifier and region if established. A generated illustrative image is not evidence of a clinical finding unless a separately corroborated report supports the finding; label synthetic imagery.

## Workflow
1. Decompose a draft sentence into atomic, falsifiable propositions.
2. Resolve exact source versions and excerpts for each proposition, including **both sources** of comparisons.
3. Link support AND conflicting evidence with explicit roles; log whether the cited fragment directly says what the report claims.
4. Reject citations that only point to search results, an agent summary or a hidden answer key.
5. Expose a citation resolution API compliant with `frontend-backend-contract.md`, returning metadata and authorized viewer locator.
6. Render clickable citations and highlighted source spans; indicate missing anchors, unsaved content, approximate OCR spans and revised documents.
7. Before final report publication, validate all essential facts and contradictions for link completeness.

## Common failure conditions
- Citation points to correct document but wrong version or page.
- Link resolves to patient overview instead of the cited clinical assertion.
- Lab specimen **collection** time is cited as result verification time.
- Medication prescription is cited as proof of actual administration.
- A report claim says 'X caused Y' but sources only establish chronology; rewrite as temporal association with limitations.
- A referenced source no longer available: show a broken provenance warning, not silent substitution.

## Acceptance tests
- Given a chronology claim comparing two visits, two independent source anchors resolve correctly.
- Given a superseded note, the link opens archived version with amendment context, not the replacement.
- Given an unauthorized patient record, citation resolver returns a non-disclosing forbidden/not-found response.
- Given an OCR-only PDF, excerpt shows extraction method/uncertainty.
- Given intentionally wrong citation text, validation rejects publication or marks it requiring human review.

## Definition of done
For every major report statement, a reviewer can click through to inspect source text, value, event-time semantics and contradictory records without relying on the agent's authority.
