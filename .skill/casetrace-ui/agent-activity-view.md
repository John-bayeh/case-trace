# Agent Activity View Skill

## Purpose
Show genuine multi-agent orchestration as an auditable sequence of tool calls and results.

## Inputs
Canonical agent events: IDs, run ID, agent identity/role, action/tool name, status, server timestamp, parameters sanitized by backend, output references and errors.

## Display
- Activity feed with agent name, phase, actual action, timestamps, duration if supplied, and status.
- Expand tool invocation to show safe parameter summary and returned record counts/references; do not reveal secrets or internal hidden reasoning.
- Distinguish planned, running, succeeded, failed, retried, and skipped. Tool calls cannot be inferred from animated placeholders.

## Event handling
Handle stream replay/reconnect with event ID and sequence ordering. Show backend-produced execution records; no fabricated timers or artificial success events.

## Security
Redact tokens, private configuration, raw credentials, and excess sensitive data; render tool payloads as escaped text or validated structured fields.

## Tests
Duplicate/reordered events, errors, retries, disconnections, two agents in parallel, unknown tool names, missing output artifacts.

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
