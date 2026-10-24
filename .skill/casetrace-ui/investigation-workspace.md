# Investigation Workspace Skill

## Purpose
Create the control center for launching, observing, and inspecting one CASETRACE investigation.

## Inputs / outputs
Inputs: patient ID, case ID, investigation ID, authorized record snapshot, event stream, findings, linked evidence. Output: explorable synchronized workspace.

## User flow
- From patient chart select **Start investigation**; confirm exact patient and case in request.
- Show queued → running → completed / failed / cancelled lifecycle, with explicit backend status.
- Display progressive phases: search, retrieval, timeline assembly, contradictions, verification, report (phase names map to backend).
- Allow source inspection during execution; do not block navigating away.
- On reconnect, fetch canonical investigation snapshot, then resume event stream with cursor if supported.

## Component contracts
`InvestigationHeader`, `InvestigationPhaseStepper`, `FindingFeed`, `TimelinePane`, `EvidenceDrawer`, `AgentActivityPane`, `InvestigationStatus`. All typed and independently testable.

## State
Server: investigation status, event history, findings, tool calls. UI: active tab, selected event, drawer open, sort/filter; URL scoped by investigation ID. Deduplicate stream messages by server IDs.

## Edge cases
Wrong patient, expired auth, conflicting run IDs, transient disconnect, delayed report, rerun. Never display success merely because streaming ended.

## Shared implementation rules
- Use Next.js App Router, TypeScript, accessible semantic components, and the existing CASETRACE design system. Reuse the supplied HTML prototypes as visual references, not as runtime data sources.
- Honor `frontend-architecture.md`, `frontend-backend-contract.md`, `case-schema.md`, `agent-tools.md`, and `hospital-api.md` when available; those contracts override example names here. Do not fabricate API fields or silently rename contract keys.
- Render only records and tool events provided by the backend. Never create investigation findings in the browser, infer clinical conclusions, or read ground-truth answer keys.
- Every evidence-related link must resolve through stable case/patient/encounter/resource IDs to a source record, document page, or image; show a safe fallback if the target is unavailable.
- Show loading, empty, error, unauthorized, stale, and partial-result states. Preserve case scope across navigation; avoid leaking cached data between patients.
- Distinguish recorded clinical timestamps from ingestion, retrieval, and agent-execution times; label timezone and precision where necessary.
- Treat all cases as synthetic demo data. Add a conspicuous `SYNTHETIC DEMO — NOT FOR CLINICAL USE` label in clinical views and exported reports.
- Maintain keyboard navigation, meaningful focus states, accessible table headers, readable contrast, and reduced-motion support.

## Definition of done
- Component has typed inputs, meaningful states, responsive layout, and accessible interaction.
- Actions are connected to contract-backed handlers; no inert demo buttons or hardcoded claims.
- Unit/component tests cover state transitions and empty/error paths; at least one integration test checks evidence deep-linking and patient isolation.
