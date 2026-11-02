# Phase 34 — API-Sports zero-daily-quota one-shot status probe

Status: **PREPARED / NOT EXECUTED**

Official API-Sports NFL/NCAA documentation was rechecked on 2026-11-02. It documents:

- `GET https://v1.american-football.api-sports.io/status`;
- authentication with `x-apisports-key`;
- the statement that this `status` call does **not** count against the daily quota;
- four response rate-limit headers covering daily and per-minute limits.

## Privacy boundary
The status response can expose account, subscription and usage information. The probe validates that body only in memory. It never prints or writes raw JSON, account identifiers, subscription fields, exact quota balances, or response headers.

The receipt records only provider, fixed endpoint, product label, sanitized PASS/HOLD category, integer diagnostic when needed, GitHub provenance, and the fact that the endpoint is documented by the provider as zero daily-quota cost. It does **not** claim that the endpoint is outside per-minute rate limits.

## Execution safeguards
- manual workflow only;
- main branch only;
- both inputs default to NO;
- independent privacy/rate-limit review plus one-request approval;
- exactly one GET path;
- direct HTTPS with environment proxies disabled;
- no redirect follow-up and no retry loop;
- 10-second request timeout;
- 64 KiB response cap;
- no error-body parsing or provider-message logging;
- receipt integrity/schema verification before publishing the Actions summary.

A PASS would prove only that one API-Sports American Football key authenticated against `/status` and that the generic status/rate-header contracts passed. It would not prove live game feeds, injuries, player statistics, prop coverage, freshness, model calibration, or forecast accuracy.

No provider request or credential read occurred while preparing this phase.


## Header compatibility correction
API-Sports warns that extra application headers may cause API errors. The probe therefore intentionally supplies only the documented `x-apisports-key` application header and clears urllib's default `User-Agent` header list. Standard transport headers required by the HTTP stack are not treated as application-level API headers.
