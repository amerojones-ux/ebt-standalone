# Phase 26 — The Odds API one-shot zero-credit authentication probe

Status: **PREPARED / NOT EXECUTED**

Official The Odds API v4 documentation was rechecked on 2026-11-02. The `GET /v4/sports?apiKey=...` endpoint is documented as not affecting usage quota and returns `x-requests-remaining`, `x-requests-used`, and `x-requests-last` headers.

## Execution safeguards
- Manual `workflow_dispatch` only; both controls default to **NO**.
- Independent account/endpoint review confirmation plus separate one-request approval.
- Fixed HTTPS host `api.the-odds-api.com` and path `/v4/sports`.
- Exactly one request path; no retries; redirect follow-ups blocked at transport level.
- 10 second request timeout; 2 minute job timeout.
- Response body capped at 256 KiB; error body capped at 4 KiB.
- API key remains only in the query parameter required by the provider and is never printed.
- Full request URL, headers, raw body, provider messages, and exact quota balance are never printed or written to the receipt.
- PASS requires HTTP 200, exact host/path, all documented quota headers, `x-requests-last == 0`, and the strict sports schema.
- A nonzero last-request usage cost is an immediate HOLD.
- Documented provider errors such as INVALID_KEY, DEACTIVATED_KEY, EXCEEDED_FREQ_LIMIT and OUT_OF_USAGE_CREDITS map to sanitized internal categories.

## Evidence boundary
This probe can establish only that one credential authenticated against the zero-credit sports catalog endpoint and that the returned schema/quota headers passed checks. It cannot establish bookmaker accuracy, player-prop coverage, forecast quality, model calibration, or production readiness.

Sportsbook market data remains comparison-only after the independent Black Diamond forecast is locked. It must not be used to increase forecast probability, cushion, calibration or certification.

No API request has been executed by this phase.
