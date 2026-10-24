# Investigation Demo Flow

## Purpose
Specify the observable end-to-end sequence from simulated hospital search to evidence-backed final report.

## Scene sequence
### 1. The ordinary chart
Open the simulated hospital dashboard; search for the synthetic CASE-001 patient. Display demographics marked synthetic, visit summary, and a clinical question without spoiling the contradiction.

### 2. Open investigation
Start a new run for the selected patient with a transparent objective: reconstruct the key event timeline and check for discrepancies. Capture `run_id`, initial status, and request correlation ID from implemented API.

### 3. Agent retrieves source material
Show actual calls to hospital tools (search, encounters, notes, labs, medications, imaging/documents as applicable). Activity feed must mirror backend events and show in-progress, success, and failure states; never invent activity cards.

### 4. Timeline assembly
Display each relevant event with source record ID, event/recorded times, time zone or uncertainty, encounter relation, and direct evidence link. If timestamps are ambiguous, keep that ambiguity visible.

### 5. Detect and challenge contradiction
Agent compares events and identifies a candidate inconsistency. Require it to query both source records, test alternative explanations (e.g. entry delay, documented correction, different time basis), and preserve unresolved uncertainty.

### 6. Reveal evidence
Present the contradiction side-by-side with contextual highlights and original documents. Clearly distinguish patient report, measured result, order, administration, and retrospective note when relevant.

### 7. Final report
Show evidence-linked chronology, reasoning summary, alternative explanations, confidence as evidentiary strength (not diagnosis likelihood), limitations, and citations that open the exact source.

## State machine (illustrative)
`idle -> preparing -> retrieving -> reconstructing -> validating -> completed`
Error branches: `failed`, `partial`, `cancelled`; resume/retry per implemented backend semantics only. Map actual event names from frontend-backend contract; do not hard-code an invented API.

## Instrumentation
Persist `run_id`, `case_id`, dataset version, ordered tool events, references, latency summaries, and failure reasons. Never expose hidden answer-key contents in events.

## Acceptance test
From a fresh reset, one launch reaches a report; source links work after reload; agent activity corresponds to persisted tool logs; viewer can distinguish discovery from claims not yet verified.
