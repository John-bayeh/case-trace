## Refactor 07 implementation direction

The current Refactor 07 request supersedes the Refactor 01 advice against a
feature tree: migrate existing domain functionality incrementally into `features/`.
Routes compose features; shared components contain no feature dependencies.
Typed domain adapters stay in `lib/api`, contracts in `types`, streaming in
`lib/sse`. Evidence selection and grouping belong to evidence, not its renderer.
Retain the existing scoped read hooks for this milestone: reads are cancelled on
identity change, explicit retry refetches, and REST reconciles live activity.
There is no cross-route cache or query invalidation promise. TanStack Query is
deferred until shared clinical queries warrant a cache; adding it solely for
file migration would create a second lifecycle beside the working SSE owner.
No new library, backend endpoint or clinical screen is required.

# CASETRACE

## Refactor 09 investigation composition

`/investigations` uses the existing paginated history API; `/investigations/new`
selects imported patients and reuses the patient-chart idempotent launch control.
The workbench retains `useInvestigation` as its single REST/SSE owner. Workflow
and recent activity derive from committed events; repeated agent executions are
displayed separately from role summaries. Task/lead inspection shows safe event
fields and links follow-up outcomes through persisted task IDs.

`lib/api/tool-audit.ts` validates the additive paginated `/tools` read model.
ToolInspector owns a cancellable, version-scoped read only while the activity
view is mounted. It displays retained audit metadata, never reconstructed results.
ClinicalContext reads the existing inventory summary without loading the chart.

`/investigations/[id]/evidence` owns finding/relationship selection and reuses
SourcePanel, source grouping and exact Unicode highlights. It reconstructs anchors
from persisted finding membership; identifier-only comparison parameters restore
multiple source selections after refresh. Hospital-source return links include
workbench, explorer and report. Reports consolidate a unique type+ID source index.
No query library, new execution engine, clinical conclusions or runtime fixtures
were introduced. See [implementation and acceptance gaps](refactoring/13-investigation-workspace-refactor-report.md).

For the audited implementation and retained product gaps, see the
[Refactor 01 matrix](refactoring/02-specification-gap-matrix.md) and
[contract compatibility decisions](refactoring/04-contract-compatibility.md).
Historical route/DTO examples below do not add public endpoints. The case library,
clinical detail views and investigation inventory remain product requirements;
their absence from the Phase 4 scope does not make them obsolete.

Use pnpm for the single Next.js App Router application. See [development stack](development-stack.md) for toolchain policy and [Phase 4 development](phase-4-development.md) for implemented routes, typed clients, REST/SSE reconciliation, evidence navigation and tests. Later implementation notes supersede historical illustrative routes/DTOs below.
## Frontend Architecture & Implementation Specification

**Version:** 1.0  
**Application:** CASETRACE Hospital & AI Investigation Workspace  
**Frontend stack:** Next.js, TypeScript, Tailwind CSS, shadcn/ui  
**Backend integration:** FastAPI  
**Primary objective:** Deliver a realistic hospital records interface and an interactive, evidence-driven AI investigation experience.

---

# 1. Product Vision

CASETRACE is a healthcare investigation platform in which clinicians, researchers, or evaluators can inspect synthetic patient records and launch AI investigations across fragmented clinical histories.

The frontend has two connected environments:

1. **Hospital Workspace:** Where patients, encounters, clinical documents, laboratory results, medications, and imaging studies live.
2. **Investigation Workspace:** Where AI agents retrieve those records, reconstruct timelines, identify contradictions, verify evidence, and generate investigation reports.

These environments must share the same underlying data and identifiers. When an agent retrieves a laboratory report, the user should be able to open that exact report in the Hospital Workspace.

### Core user experience

A user selects a patient, reviews the available medical history, launches an investigation, watches real agent activity, and examines the resulting evidence-backed findings.

### Frontend design principles

- Evidence first, visual decoration second.
- Hospital-grade information density without overwhelming the user.
- Every finding links to its original source.
- Real backend state drives the UI; no fabricated agent activity.
- Every case is navigable, regardless of which document types it contains.
- Synthetic data is visibly labeled throughout the application.
- Loading, empty, error, and partial-result states are first-class UI states.

---

# 2. Application Information Architecture

The application should have three major areas.

## A. Hospital Workspace

Purpose: Explore the simulated hospital and its patient records.

Features:
- Hospital dashboard.
- Patient directory.
- Patient chart.
- Encounter history.
- Laboratory results and trends.
- Medication history.
- Clinical notes.
- Imaging studies.
- Clinical document viewer.

## B. Investigation Workspace

Purpose: Observe and inspect AI investigations.

Features:
- Investigation list.
- New investigation flow.
- Investigation overview.
- Live agent activity.
- Tool execution history.
- Reconstructed timeline.
- Contradiction and evidence explorer.
- Final investigation report.

## C. Case Management

Purpose: Browse the ten prepared synthetic cases and understand their available records.

Features:
- CASE-001 through CASE-010.
- Case metadata and patient summary.
- Encounter count.
- Available artifact categories.
- Investigation history.
- Case readiness and data availability.

The initial implementation does not require a full administrative system or clinical data-entry workflow. The hospital should feel functional, but its scope should remain focused on record exploration and investigation.

---

# 3. Route Structure

Use the Next.js App Router.

```text
apps/web/app/
├── layout.tsx
├── page.tsx
├── cases/
│   ├── page.tsx
│   └── [caseId]/
│       └── page.tsx
├── patients/
│   ├── page.tsx
│   └── [patientId]/
│       ├── page.tsx
│       ├── encounters/
│       │   └── [encounterId]/
│       │       └── page.tsx
│       ├── timeline/
│       │   └── page.tsx
│       ├── labs/
│       │   └── page.tsx
│       ├── medications/
│       │   └── page.tsx
│       ├── imaging/
│       │   └── page.tsx
│       └── documents/
│           └── page.tsx
├── documents/
│   └── [documentId]/
│       └── page.tsx
└── investigations/
    ├── page.tsx
    ├── new/
    │   └── page.tsx
    └── [investigationId]/
        ├── page.tsx
        ├── evidence/
        │   └── page.tsx
        └── report/
            └── page.tsx
```

### Route behavior

- `/` opens the main dashboard.
- `/cases` lists CASE-001 through CASE-010.
- `/cases/CASE-001` opens a case overview.
- `/patients/SYN-001` opens the patient chart.
- `/documents/DOC-001` opens a specific clinical document.
- `/investigations` lists investigation runs.
- `/investigations/INV-001` opens the live investigation workspace.
- `/investigations/INV-001/evidence` opens the evidence explorer.
- `/investigations/INV-001/report` opens the completed report.

Use stable backend identifiers for routes. Case IDs, patient IDs, encounter IDs, and document IDs must remain distinct.

---

# 4. Global Application Shell

The global shell should look like professional clinical software, not a consumer AI chat application.

## Primary navigation

Use a collapsible left sidebar.

- Overview
- Cases
- Patients
- Investigations

The top navigation contains:

- CASETRACE logo.
- Global search.
- Current workspace or environment indicator.
- Notifications for investigation events, if implemented.
- User profile or demo identity.
- Synthetic environment indicator.

### Persistent visual indicators

Show a clear **SYNTHETIC DATA — DEMONSTRATION ENVIRONMENT** label in the application shell and on document previews.

Never rely on a small disclaimer hidden only in the footer.

### Layout behavior

- Desktop-first, optimized for a 1440px-wide presentation.
- Minimum supported desktop layout around 1024px.
- Tablet layouts should collapse secondary panels and navigation.
- Mobile layouts should remain usable for browsing records, but the full investigation console is optimized for desktop.

---

# 5. Dashboard Specification

The dashboard should communicate what is available and what the user can do next.

## Main content

### Header

**Title:** Hospital Overview

**Subtitle:** Explore synthetic patient records and investigate complex clinical histories.

Primary action: `Start Investigation`

Secondary action: `Browse Cases`

### Summary cards

- Available cases.
- Synthetic patient records.
- Total encounters.
- Available clinical documents.
- Recent investigations.

These numbers must be calculated from backend responses, not hardcoded.

### Recent cases

Display case ID, patient display name, age, encounter count, available document categories, and last activity.

### Recent investigations

Display:
- Investigation ID.
- Patient or case.
- Current status.
- Creation time.
- Last meaningful event.
- Link to resume or inspect the investigation.

### Empty state

If no investigations exist, explain that the user can select a case and start the first investigation.

---

# 6. Case Directory

The `/cases` page is the main entry point for the CASE-001 through CASE-010 dataset.

## Case card design

Each card should display:

- Case identifier.
- Synthetic patient name.
- Age and relevant demographic information.
- Short, neutral case summary.
- Number of encounters.
- Number of available documents.
- Available modalities.
- Previous investigation status, if applicable.

Use small category labels for artifacts such as:

`Clinical Notes` · `Labs` · `Medications` · `Radiology` · `Imaging` · `Referrals`

Only display categories that actually exist in the selected case.

### Filters

- Case ID.
- Available document type.
- Encounter count.
- Investigation status.
- Search by synthetic patient identifier.

### Actions

- `Open Patient Chart`
- `View Case Records`
- `Start Investigation`

The case directory must not expose hidden ground-truth answers, intended contradictions, or evaluator-only metadata.

---

# 7. Patient Chart

The patient chart is the most important part of the simulated hospital experience.

## Header

Display:
- Patient identifier.
- Synthetic patient name.
- Age and relevant demographics.
- Record status.
- Encounter count.
- Last recorded encounter.
- `Start Investigation` action.

Avoid displaying unnecessary personal information.

## Chart navigation

Use a patient-specific secondary navigation:

- Overview
- Timeline
- Encounters
- Labs
- Medications
- Imaging
- Documents

### Overview

Show:
- Patient summary.
- Encounter chronology preview.
- Recent laboratory measurements.
- Current and historical medication records.
- Recent diagnostic reports.
- Available document categories.

### Encounter list

Each encounter should show:
- Encounter date.
- Department or service.
- Encounter type.
- Encounter status.
- Primary clinician or author when available.
- Associated documents.
- Relevant recorded observations.

Selecting an encounter opens its detail page.

### Important UX rule

Do not collapse all records into one generated patient summary. Preserve the original records as separate, inspectable artifacts.

---

# 8. Clinical Timeline

The timeline is central to CASETRACE's primary demo.

## Timeline design

Present a chronological list with clear date markers.

Each event includes:
- Event date and time, when known.
- Documentation date and time, when known.
- Event type.
- Encounter reference.
- Short description.
- Source document link.

Supported event types include:
- Clinical encounters.
- Symptom documentation.
- Laboratory observations.
- Medication orders or changes.
- Diagnostic reports.
- Imaging studies.
- Referrals.
- Follow-up notes.

### Date semantics

The UI must distinguish:
- Clinical event time.
- Encounter time.
- Specimen collection time.
- Report issuance time.
- Documentation or entry time.

If timestamps conflict, display the underlying values rather than silently sorting away the discrepancy.

### Investigation overlays

During an investigation, the timeline may display:
- Candidate discrepancies.
- Verified contradictions.
- Evidence referenced by agents.
- Findings awaiting verification.

These markers must be based on actual backend results.

### Interactions

- Click an event to open its source.
- Filter by event type.
- Jump to the associated encounter.
- Compare selected events.
- Highlight evidence used in a particular finding.

---

# 9. Multimodal Clinical Document Viewer

This is a core differentiator. The application should make synthetic records look like a cohesive hospital archive, not a folder of raw JSON files.

## Supported document types

### Clinical notes

Render:
- Document title.
- Encounter and author metadata.
- Recorded date and time.
- Chief complaint.
- History of present illness.
- Relevant medical history.
- Review of systems.
- Examination findings.
- Assessment and plan.
- Follow-up instructions.

Only render sections present in the source document.

### Prescriptions and medication records

Render:
- Medication name.
- Strength and dosage.
- Route and frequency.
- Start and end dates when documented.
- Prescriber.
- Order date.
- Status.
- Associated encounter.
- Reconciliation notes.

Clearly distinguish an order from evidence that a patient actually took the medication.

### Laboratory reports

Render:
- Test name.
- Value.
- Unit.
- Reference interval.
- Abnormality indicator where supported by the source.
- Specimen collection time.
- Report time.
- Laboratory or department.
- Linked encounter.

Include historical trends for measurements with compatible units and meanings.

Do not compare incompatible measurements merely because they share a display name.

### Radiology reports

Render:
- Modality.
- Body region.
- Study date.
- Reporting author.
- Findings.
- Impression.
- Recommendations, if documented.
- Linked imaging assets.

### Synthetic imaging assets

Provide:
- Image preview.
- Full-size viewer.
- Zoom controls.
- Pan controls when practical.
- Modality and study metadata.
- Source report link.
- Synthetic image watermark.

If a case contains multiple images, allow navigation between them.

Do not imply that an illustrative generated image is an authentic radiological study. Label it accurately.

### Referral documents and encounter summaries

Render:
- Referring department or clinician.
- Destination service.
- Reason for referral.
- Relevant history.
- Request date.
- Associated encounter.
- Source document.

### Scanned-style documents and PDFs

Use a PDF viewer for actual generated PDF artifacts.

Support:
- Page navigation.
- Zoom.
- Fit-to-width.
- Download or open-original action when permitted.
- Document metadata.
- Links back to the patient chart and encounter.

For image-based scans, display the original image or PDF pages rather than pretending the document is editable text.

## Viewer layout

Use a three-part layout:

1. **Left:** Document list or encounter context.
2. **Center:** Main document or image viewer.
3. **Right:** Metadata, source information, and links to related records.

On smaller screens, collapse the side panels into drawers.

---

# 10. Laboratory Trends and Medication History

These deserve dedicated views because they provide useful evidence during investigations.

## Laboratory trends

Features:
- Select an analyte.
- Display dated measurements.
- Show values and units.
- Indicate reference ranges when available.
- Open the source report for each point.
- Identify missing measurements without interpolation that implies a real result.

Use line charts for suitable longitudinal measurements and tables for precise values.

The source record remains authoritative; charts are a visualization of the stored data.

## Medication history

Display medication records as a timeline or table.

Include:
- Medication.
- Strength.
- Dose.
- Route.
- Frequency.
- Recorded start and end dates.
- Order status.
- Encounter.
- Source record.

Where records disagree, display the conflicting information and its provenance rather than selecting one version without explanation.

---

# 11. New Investigation Flow

Launching an investigation should be simple.

## Step 1 — Select a patient

Choose an existing synthetic patient or navigate here from a case card.

## Step 2 — Configure the investigation

Display:
- Patient identifier.
- Available record categories.
- Investigation objective.
- Optional date range.
- Selected investigation profile.

For the hackathon, provide a default profile such as:

**Full Record Investigation**

Retrieve relevant records, reconstruct the chronology, examine longitudinal findings, investigate contradictions, and produce an evidence-backed report.

Avoid a large configuration form. The demo should be launchable in a few clicks.

## Step 3 — Start

Click `Start Investigation`.

The frontend sends the request to the backend and receives an investigation ID. Navigate to that investigation's live workspace.

Do not display a successful launch until the backend confirms that the investigation was created.

---

# 12. Live Investigation Workspace

This is the main presentation screen and should receive the greatest UI/UX attention.

## Recommended desktop layout

Use a three-column investigation workspace.

### Left column — Patient and records

Width: approximately 250–290px.

Contains:
- Patient summary.
- Available encounters.
- Record categories.
- Retrieved document list.
- Retrieval status.

### Center column — Agent activity

Flexible width.

Contains:
- Investigation progress.
- Active agent.
- Agent tasks and statuses.
- Actual tool calls.
- Retrieval results.
- Candidate findings.
- Verification events.

### Right column — Evidence and findings

Width: approximately 320–360px.

Contains:
- Selected finding.
- Supporting evidence.
- Conflicting evidence.
- Source links.
- Verification status.

Allow the side panels to collapse so the central activity remains readable.

## Investigation status model

Support:
- Queued.
- Running.
- Waiting for additional retrieval.
- Verifying.
- Completed.
- Completed with limitations.
- Failed.
- Cancelled, if cancellation is implemented.

The status must reflect the backend workflow state.

## Agent activity cards

Each card displays:
- Agent name.
- Responsibility.
- Current status.
- Current task or latest completed task.
- Tools actually executed.
- Records retrieved.
- Findings produced.
- Error details where applicable.

Avoid displaying fabricated internal thoughts or lengthy simulated conversations.

Instead, show observable activity, concise explanations, and verifiable outputs.

## Tool execution inspector

When a tool call is selected, display:
- Tool name.
- Execution status.
- Safe, human-readable parameters.
- Start and completion times.
- Duration, when measured.
- Returned record IDs.
- Result summary.
- Error message, if any.

Sensitive fields should be redacted where appropriate, even in a synthetic environment.

## Live updates

Use Server-Sent Events (SSE) for a straightforward initial implementation.

The backend emits typed events, and the frontend updates the activity stream without repeatedly reloading the page.

Examples of event types:

```text
investigation.started
agent.started
tool.started
tool.completed
tool.failed
records.retrieved
finding.proposed
finding.verified
finding.rejected
investigation.completed
investigation.failed
```

Persisted investigation state must remain recoverable after refresh. SSE is a delivery mechanism, not the source of truth.

If the connection drops, show a reconnecting state and fetch the latest investigation snapshot.

---

# 13. Evidence Explorer

The Evidence Explorer allows users to inspect how CASETRACE arrived at its conclusions.

## Evidence finding panel

Each finding should contain:
- Finding ID.
- Concise claim.
- Finding category.
- Verification status.
- Supporting source records.
- Conflicting source records.
- Relevant dates and values.
- Limitations.
- Related timeline events.

## Evidence interactions

Users should be able to:
- Open a cited source.
- Jump to the relevant section of a document.
- Compare two conflicting records.
- View the source event on the timeline.
- Inspect the verification history.
- Navigate back to the investigation.

### Source highlighting

When possible, highlight the exact paragraph, table row, or document section that supports the claim.

If precise section-level anchoring is not available, open the source document and clearly identify the relevant page or section.

Never show a source citation that resolves to the wrong record.

---

# 14. Final Investigation Report

The final report should feel like a professional evidence review.

## Report structure

### A. Executive summary

A concise overview of the investigation and its principal findings.

### B. Reconstructed chronology

A chronological presentation of important events, including unresolved timestamp conflicts.

### C. Verified contradictions

For each contradiction:
- What conflicts.
- The records involved.
- Relevant timestamps.
- Why the discrepancy matters.
- Verification status.

### D. Longitudinal findings

Relevant laboratory trends, medication relationships, and other patterns supported by the records.

### E. Supporting and conflicting evidence

Show the strongest evidence for each interpretation and the records that limit or challenge it.

### F. Unresolved questions

List missing information, ambiguous documentation, and additional evidence that would help resolve the case.

### G. Provenance and limitations

Include source references, investigation metadata, and an explicit statement that the case is synthetic and the report is not a validated clinical diagnosis.

## Report actions

- Open cited evidence.
- Return to the investigation.
- Copy a finding.
- Export or print the report, if implemented.

PDF report generation can be added after the interactive report is stable.

---

# 15. Frontend Component Architecture

Organize components by product domain rather than placing the entire application in a generic components directory.

```text
apps/web/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── cases/
│   ├── patients/
│   ├── documents/
│   └── investigations/
├── components/
│   ├── layout/
│   │   ├── app-sidebar.tsx
│   │   ├── app-header.tsx
│   │   └── environment-banner.tsx
│   ├── shared/
│   │   ├── status-badge.tsx
│   │   ├── empty-state.tsx
│   │   ├── error-state.tsx
│   │   ├── loading-state.tsx
│   │   └── source-link.tsx
│   └── ui/
├── features/
│   ├── cases/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api.ts
│   ├── patients/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api.ts
│   ├── encounters/
│   ├── timeline/
│   ├── labs/
│   ├── medications/
│   ├── documents/
│   │   ├── clinical-note-viewer.tsx
│   │   ├── lab-report-viewer.tsx
│   │   ├── prescription-viewer.tsx
│   │   ├── radiology-report-viewer.tsx
│   │   ├── imaging-viewer.tsx
│   │   └── pdf-viewer.tsx
│   └── investigations/
│       ├── components/
│       │   ├── investigation-header.tsx
│       │   ├── agent-activity-list.tsx
│       │   ├── agent-status-card.tsx
│       │   ├── tool-execution-panel.tsx
│       │   ├── evidence-panel.tsx
│       │   └── finding-card.tsx
│       ├── hooks/
│       ├── api.ts
│       ├── events.ts
│       └── types.ts
├── lib/
│   ├── api-client.ts
│   ├── query-client.ts
│   ├── formatters.ts
│   └── validators.ts
├── types/
│   ├── patient.ts
│   ├── encounter.ts
│   ├── clinical-record.ts
│   ├── document.ts
│   └── investigation.ts
└── tests/
```

This is the intended organizational structure, not a requirement to create empty files for every entry immediately. Build modules when their corresponding features are implemented.

---

# 16. Frontend Data Contracts

Use TypeScript types generated from or validated against the FastAPI/Pydantic schemas wherever practical.

Avoid defining independent, incompatible representations of the same record across features.

## Core types

```typescript
type CaseId = string;
type PatientId = string;
type EncounterId = string;
type DocumentId = string;
type InvestigationId = string;

type InvestigationStatus =
  | "queued"
  | "running"
  | "waiting_for_retrieval"
  | "verifying"
  | "completed"
  | "completed_with_limitations"
  | "failed"
  | "cancelled";

type ArtifactType =
  | "clinical_note"
  | "prescription"
  | "laboratory_report"
  | "radiology_report"
  | "imaging_asset"
  | "referral"
  | "encounter_summary"
  | "other";

interface SourceReference {
  documentId: DocumentId;
  encounterId?: EncounterId;
  section?: string;
  page?: number;
  recordLocator?: string;
}

interface ClinicalDocument {
  id: DocumentId;
  patientId: PatientId;
  encounterId?: EncounterId;
  type: ArtifactType;
  title: string;
  eventDate?: string;
  authoredAt?: string;
  mimeType?: string;
  available: boolean;
}

interface InvestigationFinding {
  id: string;
  claim: string;
  status: "proposed" | "verified" | "rejected" | "unresolved";
  supportingEvidence: SourceReference[];
  conflictingEvidence: SourceReference[];
  limitations: string[];
}
```

These are frontend-facing examples. The final contract must be reconciled with the actual backend response schemas.

### Data rules

- Represent dates using ISO 8601 timestamps where appropriate.
- Preserve the original source timestamps.
- Do not fabricate values for missing fields.
- Distinguish `null`, absent fields, and empty arrays where the API contract requires it.
- Validate incoming events at runtime.
- Never infer verification status from a visual badge or client-side heuristic.

---

# 17. State Management and API Integration

Use a small, maintainable set of frontend data tools.

### Server state

Use TanStack Query for:
- Fetching patient records.
- Caching encounter data.
- Loading document metadata.
- Fetching investigation snapshots.
- Invalidating stale data after updates.

### Local UI state

Use React state or a lightweight store for:
- Selected encounter.
- Open side panels.
- Timeline filters.
- Selected evidence finding.
- Viewer zoom level.
- Temporary UI preferences.

Do not copy all server data into a separate global store without a specific reason.

### API client

Create one typed API client responsible for:
- Base URL configuration.
- Request serialization.
- Response validation.
- Error normalization.
- Authentication headers when introduced.
- Consistent handling of HTTP failures.

Configure the API base URL through environment variables, for example:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Use the actual backend port and deployment URL in the final environment configuration.

### Core frontend API operations

```text
GET  /api/cases
GET  /api/cases/{caseId}
GET  /api/patients
GET  /api/patients/{patientId}
GET  /api/patients/{patientId}/encounters
GET  /api/patients/{patientId}/documents
GET  /api/documents/{documentId}

POST /api/investigations
GET  /api/investigations
GET  /api/investigations/{investigationId}
GET  /api/investigations/{investigationId}/events
GET  /api/investigations/{investigationId}/report
```

These are proposed contracts; coordinate the final paths and payloads with the backend implementation.

Use a separate streaming endpoint for SSE if the backend exposes one. Document and imaging assets should be served through controlled asset endpoints or authorized URLs, not embedded as large base64 strings in general API responses.

---

# 18. Visual Design System

## Design direction

**A modern clinical investigation workstation.**

The interface should combine the clarity of professional medical software with the sophistication of an AI research platform.

Avoid:
- Excessive gradients.
- Oversized marketing-style cards.
- Excessive animation.
- Decorative AI brain imagery.
- Chat bubbles for every agent action.
- Dense walls of unstructured text.

## Color system

Use a restrained neutral foundation with a cool blue accent.

| Purpose | Treatment |
|---|---|
| Main background | Neutral light gray or off-white |
| Primary surfaces | White |
| Primary text | Dark slate |
| Secondary text | Muted gray |
| Primary action | Blue |
| Successful retrieval | Green |
| Candidate finding | Amber |
| Verified discrepancy | Strong but restrained warning color |
| Failure | Red |
| Borders | Subtle neutral gray |

Status must be communicated through text and icons as well as color.

## Typography

- Use a highly legible sans-serif font.
- Use compact but readable typography for record metadata.
- Use stronger hierarchy for page titles and patient identifiers.
- Use tabular numerals for laboratory values and timestamps where appropriate.
- Use consistent date and measurement formatting.

## Spacing and density

- Use a consistent spacing scale.
- Keep metadata compact.
- Preserve whitespace around findings and important warnings.
- Use sticky headers only where they materially improve navigation.
- Prefer tables for precise structured data and cards for meaningful summaries.

## Interaction design

- Provide clear hover and focus states.
- Ensure keyboard navigation works.
- Use accessible dialog and drawer components.
- Preserve scroll position when returning from a source document when feasible.
- Provide visible feedback for long-running investigations.

---

# 19. Reliability, Accessibility, and Security

## Reliability

Every data-driven view must support:
- Loading.
- Empty results.
- Partial results.
- API failure.
- Retry.
- Missing optional artifacts.

If one report is unavailable, the rest of the patient chart should remain usable.

## Accessibility

- Semantic HTML.
- Keyboard-accessible navigation.
- Proper form labels.
- Accessible dialogs.
- Visible focus indicators.
- Text alternatives for image controls.
- Non-color-only status indicators.

## Security

Even though the hackathon uses synthetic data:
- Do not expose API secrets through `NEXT_PUBLIC_` variables.
- Do not include hidden answer keys in frontend bundles.
- Do not trust client-supplied patient or document identifiers without backend authorization checks.
- Sanitize and safely render clinical document content.
- Avoid rendering arbitrary HTML from generated records.
- Do not expose sensitive tool parameters unnecessarily.
- Validate asset URLs to prevent unintended access to internal network resources.
- Keep investigation logs separate from hidden evaluator data.

---

# 20. Testing Strategy

## Component tests

Test:
- Status badges.
- Timeline events.
- Laboratory tables.
- Document viewers.
- Agent activity cards.
- Evidence panels.

## Integration tests

Verify:
- Opening a case leads to the correct patient chart.
- Every document link opens the matching document.
- Timeline events resolve to the correct encounters.
- Tool events update the investigation console.
- Verified findings link to the correct sources.
- Refreshing an investigation restores its latest state.

## End-to-end tests

The flagship scenario should be testable from start to finish:

1. Open CASE-001.
2. Inspect its patient chart.
3. Open a source laboratory report.
4. Start an investigation.
5. Observe actual agent and tool events.
6. Open the detected timeline contradiction.
7. Inspect both source records.
8. Open the final report.
9. Refresh the page and confirm that the completed investigation remains available.

## Evaluation criteria

The frontend is successful when a judge can understand what the system is doing, inspect its source records, follow the discovery, and distinguish verified evidence from hypotheses without needing a developer to explain the interface.

---

# 21. Implementation Order

Build the frontend in vertical slices, connecting each feature to the backend rather than creating a large collection of disconnected mock screens.

### Phase 1 — Foundation

- Next.js and TypeScript setup.
- Tailwind and shadcn/ui.
- Application shell.
- API client and shared types.
- Loading, empty, and error states.

### Phase 2 — Hospital environment

- Dashboard.
- Case directory.
- Patient chart.
- Encounter details.
- Clinical document viewer.
- Laboratory and medication views.
- Imaging and PDF viewer.

### Phase 3 — Investigation workspace

- Investigation creation.
- Investigation overview.
- Live event stream.
- Agent activity cards.
- Tool execution inspector.
- Evidence explorer.

### Phase 4 — Final report

- Timeline reconstruction.
- Verified contradictions.
- Evidence-linked findings.
- Unresolved questions.
- Report export if time permits.

### Phase 5 — Demo polish

- Loading and reconnect states.
- Responsive behavior.
- Source navigation.
- Accessibility checks.
- End-to-end tests.
- Rehearsal using the real synthetic dataset.

---

# 22. Definition of Done

The frontend is ready for the CASETRACE hackathon when:

1. All ten cases can be browsed without hardcoded case-specific UI.
2. The UI adapts to the available records in each case.
3. The same source documents are accessible through both the hospital interface and agent retrieval tools.
4. Clinical documents and reports render with their relevant metadata.
5. Laboratory values and timestamps are displayed accurately.
6. Imaging assets have appropriate viewing controls and synthetic-data labels.
7. An investigation can be launched and monitored through real backend events.
8. The agent activity stream reflects actual tool execution.
9. Findings link to the exact supporting or conflicting source records.
10. The final report distinguishes evidence, interpretation, and uncertainty.
11. Investigation state survives refresh.
12. The flagship demo works reliably without fabricated activity or hardcoded results.

---

## Final implementation principle

**The frontend is not merely a visualization layer. It is the interface through which the user can verify that CASETRACE actually investigated the medical record.**

The Hospital Workspace establishes the source of truth. The Investigation Workspace exposes the investigation process. The Evidence Explorer connects the final conclusion to the original records.

Build those three experiences around shared identifiers, consistent data contracts, and real backend state. That is what will make CASETRACE feel like a coherent healthcare AI system rather than a polished collection of mock screens.

## Refactor 08 hospital workspace

Hospital routes now compose case-library, chart-layout, clinical-list, encounter-detail, document-detail and hospital-source features. Patient layout shares cancellable identity/summary reads across clinical routes; section lists load targeted paged resources. Cases/history use lib/api/catalog.ts with runtime validation. The clinical record dictionary remains the evidence fallback; encounter/observation/medication/document/imaging DTO interfaces describe typed API results.

Original PDF.js rendering is lazy on asset-open; its matching worker is generated from the lockfile dependency by prebuild/predev. Only registered verified asset bytes enter object URLs; unmount revokes them. No raw case files, evaluator metadata, cached conclusions, alternate server-state store or new SSE owner are added. Scoped source+finding links re-read persisted anchors and check patient ownership. Document context/metadata are collapsible on smaller screens. See the R08 report for executed validation and limits.
