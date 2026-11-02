# Phase 18: WeatherAPI endpoint contract (reviewed; NOT executed)

Official references:
- https://www.weatherapi.com/docs/
- https://www.weatherapi.com/docs/realtime-api/
- https://www.weatherapi.com/pricing

## Proposed first live check
- Provider: WeatherAPI.com; credential environment variable: `EBT_WEATHER_API_KEY`.
- Method: GET; HTTPS host: `api.weatherapi.com`; path: `/v1/current.json`.
- Required parameters: `key` (credential) and `q` (fixed, non-personal test city).
- Restrict to one request, no redirect, no retry, timeout <=10 seconds; never output full URL (contains credential), request/response body or headers.
- Validate JSON object with `location` and `current`; require numeric `current.last_updated_epoch` and `current.temp_c`; verify expected location, UTC freshness, and finite numeric values.
- On 401/403, 429, malformed JSON, stale observation, location mismatch, or transport error: HOLD; sanitize all logging.
- Use standard current conditions only; no premium add-ons, history, or forecast calls.

## Subscription and authorization gate
Official published Free plan advertises 100,000 calls/month, but **the account's actual plan, remaining quota, billing status and authorization are not verified**. No request should be made until those are checked and one read-only test call is explicitly approved. WeatherAPI's historic endpoint may archive forecast data rather than observations; do not use it as measured ground truth for model validation.

## Status
DOCUMENTED / PENDING USER-SPECIFIC ENTITLEMENT AND COST REVIEW. No live call or API key read. Forecast activation remains HOLD.
