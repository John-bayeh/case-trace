# Document Retrieval — Skill

## Purpose
Retrieve clinical notes, referrals, consults, scanned PDFs, discharge summaries and other source artifacts as citable evidence.

## Inputs
Scoped patient and optional encounter, document type, author, time interval, keyword/filter, cursor; exact `document_id` for detail.

## Procedure
1. Query metadata first: `document_id`, encounter, type, author role, creation/signature/amendment times, status, media type, checksum/hash and artifact pointer.
2. Fetch content only through authorized document-detail or rendition tools.
3. Keep verbatim original text separately from normalized extracted text. Label OCR/extraction quality or missing text.
4. Preserve page numbers and stable evidence anchors: document ID + page + quote span/bounding box when available.
5. Return supersession/addendum lineage and avoid silently promoting drafts to signed notes.
6. Serve downloads/previews with safe temporary access and content-type controls; no raw storage traversal.
7. Do not place complete note text in audit logs or tool error messages.

## Citation anchor example
```json
{"document_id":"DOC-027","page":2,"span_id":"SPAN-004","quoted_text":"Follow-up requested within one week.","version":1}
```

## Forbidden behavior
Do not alter scanned originals, invent text unreadable in an image, cite only an AI-generated summary, or expose the private case answer key as a clinical document.

## Tests / done
Check correct page/span citation, missing blob vs. missing metadata, image-only PDF, signed/amended versions, unsafe file paths, corrupt assets and permission failures.
