# CASETRACE demo runbook

Executable preparation/reset/evaluation commands are in [Phase 5 operations](phase-5-development.md). Use the dedicated demo database; stop its API before reset. Validate assets and inspect the latest evaluation summary before presenting. Default execution is explicitly deterministic rules mode. Do not describe it as live LLM reasoning. A configured provider requires its own live acceptance run.

## Primary presentation: four minutes

| Time | Presenter action | Transition |
| --- | --- | --- |
| 0:00–0:25 | Explain that CASETRACE investigates fragmented synthetic records; this prototype is not validated clinical decision support. | Open dashboard. |
| 0:25–1:00 | Search Daniel, open the chart, browse encounters, laboratory history and original notes. | Ask what changes when records are connected. |
| 1:00–1:35 | Start a real investigation. Show actual agent/tool activity and execution mode. | Open timeline while work progresses. |
| 1:35–2:30 | Inspect the onset contradiction after it is verified. Compare June history with the earlier contemporaneous symptom event and contextual notes. | Open original sources and their distinct event/documentation times. |
| 2:30–3:10 | Review medication orders versus reported use, follow-up limitations and competing explanations. | State that temporal evidence does not establish drug causality or a final diagnosis. |
| 3:10–4:00 | Open the persisted final report, inspect citations and uncertainty, refresh to demonstrate persistence. | Close with real retrieval, temporal comparison, deterministic verification and auditability. |

Do not promise a specific runtime. Use measured results in the Phase 5 report, and disclose any partial state. The strict exact-anchor benchmark can grade discovery as partial even though a record-level contradiction is verified; do not claim a perfect benchmark.

## Ninety-second backup

Open a previously completed real investigation by its saved URL. Say explicitly: “This is a previously completed run.” Show execution mode, activity history, the contradiction's source comparison and persisted report. Do not animate replay as current activity. Keep the original database or its consistent backup: exported JSON alone does not provide a browsable replay. No prerecorded video is currently supplied.

## Recovery

- LLM unavailable: show a labeled completed real run, or explicitly select rules mode for a new run. Never silently replace failed inference.
- Slow run: inspect already persisted activity and timeline; leave its true state visible.
- Connection loss: refresh the existing investigation URL. REST restores state and SSE reconnects; do not launch repeated runs accidentally.
- Interrupted worker: startup marks interrupted work failed. Preserve its history; create a new investigation. There is no resume/cancel API.
- Missing asset: show the source-unavailable message and structured source if available. Do not fabricate a preview.
- Database issue: stop the dedicated API, retain the backup and use the approved offline reset. Never remove live WAL/SHM files or reset the normal development database.
- Partial failure: show completed-with-limitations and the actual missing work. Do not call it fully complete.
- Network outage: use a previously verified local run if services work. A recorded walkthrough must be captured from real execution and labeled; one has not been prepared here.
