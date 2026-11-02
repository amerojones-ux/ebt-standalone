# EBT.ai Provider Verification Gates — Development Specification

Status: DEVELOPMENT / HOLD for live acceptance. Branch-only documentation; no secrets or paid API calls.

## Provider inventory
| Provider | Intended role | Verified subscription | Live endpoint | Status |
|---|---|---|---|---|
| TheRundown | Sports markets / schedule | No | No | HOLD |
| Sportsdata | League statistics / availability | No | No | HOLD |
| The Odds API | Market evidence (after model lock) | No | No | HOLD |
| API-Sports | League schedules / statistics | No | No | HOLD |
| RapidAPI | Subscribed sports APIs; per-host contracts required | No | No | HOLD |
| WeatherAPI | Environmental inputs | No | No | HOLD |
| Sportradar | Official-style league feeds / statistics | No | No | HOLD |

Provider names are intended integrations, not confirmed active subscriptions. RapidAPI is an aggregator: every subscribed API host requires its own endpoint and schema contract.

## Required stages
1. INVENTORY: identify provider host, legal access terms, sport coverage, configured endpoint path and source contract.
2. SECRET_PRESENCE: report only configured/missing, never values, prefixes, hashes or credential-bearing URLs.
3. AUTHORIZATION: read-only health request, no purchases, subscription changes or credential disclosure.
4. HTTP: distinguish 200, 401, 403, 404, 429, 5xx, timeout and unexpected redirects.
5. SCHEMA: verify expected identity fields, types, units, pagination, timezone and null semantics.
6. FRESHNESS: record source-published timestamp and retrieved timestamp separately; no false freshness from refetch.
7. RECONCILIATION: compare canonical event/team/player IDs, event status, participation and statistics to official league/team evidence.
8. FAILURE: validate rate limit, missing fields, stale data, contradictory evidence and retry/backoff with bounded calls.
9. MODEL ISOLATION: build and lock independent projections before consuming any sportsbook market fields.
10. RELEASE: require reproducible tests, documented source coverage, owner approval, rollback plan and a live verification ledger.

## Decision rules
- PASS: evidence and all required gates verified for the exact endpoint and data purpose.
- HOLD: access, schema, freshness, official reconciliation, or required evidence not established.
- FAIL: observed auth failure, schema violation, integrity failure or unacceptable contradiction.
- NOT_TESTED: no actual request executed; do not conflate with failure.

Never infer API readiness from GitHub secret presence or synthetic test success.
No live forecast or approved wager may be published from this integration until V7/V7.1 evidence, calibration, MC, and exact-price gates independently pass.

## Safe test record (append-only)
provider,api_host,endpoint_id,league,data_category,contract_version,request_timestamp_utc,response_status,latency_ms,source_published_at_utc,retrieved_at_utc,schema_pass,identity_pass,official_reconciliation,rate_limit_observed,redacted_error,decision,source_evidence_id,run_id

Do not persist API keys, authorization headers, signed URLs, full sensitive request/response bodies or personal account data.

## Acceptance checks
- No secrets appear in test logs or reports.
- Missing key -> NOT_TESTED/HOLD, not PASS.
- 401/403 -> FAIL authorization, never retry with bypass.
- 429 -> HOLD with bounded backoff, no uncontrolled requests.
- HTTP 200 with missing required fields -> FAIL schema.
- Stale event timestamp -> HOLD freshness.
- Official roster/status conflict -> HOLD reconciliation.
- Provider market data cannot change locked independent forecast.
- Simulations not executed -> PENDING, never certified.
- A read-only endpoint passing does not certify all endpoints for that provider.

## Next implementation
Implement adapter contracts and fixtures on this branch; inspect existing repository paths before modifying code. Run synthetic unit tests, then opt-in read-only provider calls using existing GitHub Actions secrets without revealing values. Publish a redacted gate-by-gate ledger. Do not merge or deploy before review.
