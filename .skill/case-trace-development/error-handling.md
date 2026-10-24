# Error Handling and Recovery

## Principle
Failures must be explicit, safe, observable, and recoverable. An unavailable source is not negative clinical evidence.

## Common error envelope
Follow `frontend-backend-contract.md` if it already defines an error response. Otherwise propose, do not silently impose, this shape:

```json
{"error":{"code":"RECORD_NOT_FOUND","message":"Record not found","details":{},"request_id":"req_example"}}
```

Never return a 200 response with a misleading success flag after a required operation fails.

## Categories
| Category | Typical HTTP status | Handling |
| --- | --- | --- |
| Input/schema invalid | 400 or 422 | Point to invalid field; no stack trace |
| Unauthorized/forbidden | 401/403 | Deny access without revealing protected resources |
| Resource not found | 404 | Distinguish missing record from missing access |
| State conflict | 409 | Return stable error code and safe retry guidance |
| Rate limited | 429 | Retry only when safe, use bounded backoff |
| External tool/service unavailable | 502/503/504 | Preserve partial results with explicit incomplete status |
| Unexpected bug | 500 | Log trace with request ID; generic public error |

## Agent/tool semantics
- Return a structured error result with `tool_call_id`, `error_code`, `retryable`, and `source`; never make up tool output.
- Put partial investigations in `partial`/`blocked` state (per contract), not `complete`.
- Clearly mark a record as `not_retrieved` vs `retrieved_no_match`; the two mean different things.
- For a timed-out search, preserve verified evidence already retrieved and mark missing evidence unresolved.
- Cap retries; no unbounded recursive self-recovery.

## Frontend treatment
Provide inline retry for transient failures, specific empty states for valid no-result responses, and a clear fatal state for unrecoverable errors. Retain draft user input when possible. Do not show a clinical claim whose evidence fetch failed without warning.

## Audit and security
Sanitize exceptions and logs. Avoid including full patient data, secrets, environment variables, raw access tokens, or internal stack traces in API responses. Maintain useful trace context in server-side logs only.

## Validation
Test malformed request, missing patient/record, unavailable tool, duplicate request, partial evidence, failed citation target, network timeout, and successful retry.
