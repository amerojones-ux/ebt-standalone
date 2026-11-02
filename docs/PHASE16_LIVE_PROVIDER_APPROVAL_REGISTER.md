# Phase 16 — live provider verification approval register

**State: NOT AUTHORIZED FOR NETWORK EXECUTION.** Phase 15 offline preflight passed according to the GitHub Actions screenshots. This register is an engineering gate, not a live test.

| Provider | Exact subscription / product | Official endpoint and host | Read-only? | Cost per call / quota | Auth format | Approval |
| --- | --- | --- | --- | --- | --- | --- |
| TheRundown | Pending | Pending | Pending | Pending | Pending | HOLD |
| SportsData | Pending | Pending | Pending | Pending | Pending | HOLD |
| The Odds API | Pending | Pending | Pending | Pending | Pending | HOLD |
| API-Sports | Pending | Pending | Pending | Pending | Pending | HOLD |
| RapidAPI | Specific subscribed API and host required | Pending | Pending | Pending | Pending | HOLD |
| WeatherAPI | Pending | Pending | Pending | Pending | Pending | HOLD |
| Sportradar | Pending | Pending | Pending | Pending | Pending | HOLD |

## Execution safeguards
1. Confirm the specific product, official documentation, and allowed authentication mechanism independently for each service. A RapidAPI aggregator key does not identify which API is subscribed.
2. Obtain explicit approval of quota/charge implications before making requests. Do not infer zero cost from key presence.
3. Manual-only workflow, one selected provider at a time; never triggered on push, pull request, or schedule.
4. Hardcoded reviewed HTTPS host/path; no user-provided URL, no redirects, no retries, 10-second timeout, at most one request per approved run.
5. Mask secrets and never output headers, query strings, raw response bodies, subscription identifiers, or request exceptions containing URLs.
6. Summarize only sanitized status categories and schema checks; distinguish HTTP 200 from genuine entitlement and data validity.
7. Deny all requests until an individual provider row is approved. Any 401/403/429, malformed response, stale timestamp, identity conflict, or quota uncertainty stays HOLD.
8. Keep forecasts and wagering OFF until independent lineup, injury, history, calibration, and joint-dependence gates pass.

## Evidence required for promotion
Provider-specific endpoint approval, read-only entitlement, bounded-cost approval, successful live response with expected fields, independent cross-source identity and freshness verification, negative tests, and an audit record. Offline success is not sufficient.
