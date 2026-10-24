# Cross-Record Query — Skill

## Purpose
Enable agents to ask evidence-driven questions across encounters, labs, medications, documents and imaging, especially for the CASETRACE **timeline contradiction** demo.

## Inputs
Authenticated actor, verified patient, explicit date window, selected resource types, predicates, bounded `limit`, cursor, sort direction and investigation ID. Contract may expose a structured query DSL; **never accept arbitrary raw SQL from an agent**.

## Query design
- Enforce patient, tenant and authorized resource scope before joining.
- Allow bounded joins on canonical IDs: patient, encounter, order, report, document and study.
- Permit distinct event-time axes and return which time field each row represents.
- Expose source records, not only aggregations. Each observation needs `resource_type`, `resource_id`, event time, entered time, source/document link and query reason.
- Return stable deterministic ordering; support bounded pagination.
- Use `null` for unavailable dates/links; do not invent joins based on coincidental matching names.
- Support contradictory sources side-by-side rather than reconciling them implicitly.

## Example query (illustrative)
```json
{"patient_id":"P-001","from":"2026-04-01T00:00:00+03:00","to":"2026-05-01T00:00:00+03:00","resources":["encounters","labs","medications","documents"],"sort":{"field":"event_time","direction":"asc"},"limit":50}
```

## Example evidence event
```json
{"resource_type":"clinical_note","resource_id":"NOTE-018","event_time":"2026-04-12T08:00:00+03:00","recorded_at":"2026-04-14T15:20:00+03:00","source_document_id":"DOC-018","time_basis":"asserted_in_note"}
```

## Investigation pattern
1. Gather bounded candidate events from all applicable classes.
2. Identify suspicious time relationships (e.g. documentation predates an asserted event, follow-up note conflicts with lab report).
3. Retrieve original records using dedicated source tools.
4. Compare event claims with observation, result and recording times; keep uncertainty explicit.
5. Pass anchored observations to investigation logic; **query layer does not declare the diagnosis or mystery solved**.

## Safety and performance
Whitelist filter/sort fields; parameterize repository queries; cap joins, lookback windows, rows and total execution cost; deny cross-patient joins by default; audit caller filters without logging full records.

## Tests / done
Verify multi-type chronological ordering, identical timestamps, timezone offsets, partial data, conflicting events, bounded pagination, authorization bypass attempts, query injection and reproduction of CASE-001 contradiction only through retrievable evidence.
