# WeatherAPI.com integration contract — research only

Status: **OFFLINE CI VERIFIED; LIVE AUTH NOT TESTED; FORECAST HOLD; WAGER NOT APPROVED**.

## Official vendor contract
- Vendor confirmed by account owner: WeatherAPI.com.
- HTTPS host: `api.weatherapi.com`.
- First reviewed candidate: `GET /v1/current.json`.
- Required request parameters: `key` (credential), `q` (location).
- Use a fixed non-user location for an authentication smoke test; do not request user location.
- The documented endpoint is not yet approved for live use. This document does not grant execution permission.
- Official documentation:
  - https://www.weatherapi.com/docs/authentication/
  - https://www.weatherapi.com/docs/request/
  - https://www.weatherapi.com/docs/request-parameters/

## Transport controls — mandatory before the first live call
1. Dedicated protected runner/environment; never use a PR workflow or an untrusted fork to access the secret.
2. Restrict outbound DNS/HTTPS to the reviewed hostname with infrastructure egress controls, not Python checks alone.
3. Disable HTTP redirects, proxies not explicitly reviewed, HTTP debug logging, URL logging, APM URL capture, and verbose exception rendering. TLS verification required.
4. Retrieve `EBT_WEATHER_API_KEY` at execution time; never print, hash, persist, upload, or pass it via command arguments.
5. Bound request count, timeout, bytes read, and response schema. Stop on any unexpected hostname, status, content type or provider error.
6. Only emit sanitized provider ID, time, response category and research-only release gates; no raw URL, response body, headers, key, account ID or error text.
7. Review plan terms and retention/derived analytics rights independently before ingesting any weather observation.
8. Verify protected-environment approval and operational network restrictions separately before any workflow is enabled.

## Independent data and model gates
- Treat weather as an **environmental context feature**, never as a sportsbook market quote or independent proof of a game outcome.
- Join weather to a verified event venue and kickoff timestamp, with explicit time zone and source-as-of evidence.
- Avoid look-ahead bias: for pregame projections, use only weather forecasts issued before the forecast cutoff; postgame observed conditions are audit-only.
- Prefer venue-specific outdoor conditions. Indoor/domed events need explicit venue rules; do not apply weather uplift automatically.
- Track missingness, refresh age, weather forecast horizon, and forecast-versus-observed error separately.
- No automatic elevation from REACHABLE_ONLY to rights_verified, feed_verified, model_certified or wager_approved.

## Pending execution checklist
- [x] Vendor identity confirmed.
- [x] Offline error classification and regression CI passed (commit `7243f1b`).
- [ ] Protected network egress and URL-redaction verification.
- [ ] Reviewed query-key transport with synthetic network tests.
- [ ] Explicit approval to execute the credentialed probe.
- [ ] Live sanitized result from the protected runner.
- [ ] Subscription entitlement and historical access independently reviewed.
- [ ] Event/venue/time join, as-of snapshots and out-of-time model calibration.
