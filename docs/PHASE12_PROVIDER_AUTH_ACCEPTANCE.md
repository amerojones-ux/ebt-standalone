# Phase 12 — bounded provider authentication acceptance

Status: **HOLD** until independently observed. Secret presence alone is not authentication.

## Execution contract
- Manual opt-in only; never run on pull requests, pushes, or a schedule.
- Read-only endpoints; explicit per-provider allowlist, host and path; HTTPS only.
- No paid/chargeable calls without separate authorization and known quotas.
- At most one request per enabled provider, timeout <= 10 seconds, no redirects or retries.
- Never print credentials, request URLs containing tokens, headers, response bodies, or account identifiers.
- Emit provider name, sanitized status class, elapsed time, and rate-limit category only.
- Deny unknown providers/hosts, missing secrets, unexpected redirects, and malformed responses.
- Check each provider's authentication format, terms, subscription and quota before enabling.
- Record timestamps and provenance. No successful call is evidence of forecasting accuracy.

## Acceptance criteria
1. Explicit host/endpoint and cost review for each provider.
2. A scoped successful response with schema/identity/timestamp checks.
3. Negative tests for missing/invalid credentials, 401/403, 429, timeout, malformed JSON, redirects and partial coverage.
4. Independent fixture-free live evidence; audit log contains no sensitive material.
5. No transition to live forecasting until injury/roster identity, historical calibration and joint parlay dependence are validated.

This document is a plan, **not** an executable live workflow. No network calls were made.
