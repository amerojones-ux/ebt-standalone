# Phase 21 — WeatherAPI one-shot live authentication probe

Status: **PREPARED / NOT EXECUTED**

Official WeatherAPI documentation confirms that authentication uses the `key` query parameter and current weather is available at `/v1/current.json`. The published Free plan includes realtime weather and 100,000 calls/month, but the repository cannot infer the actual plan attached to this key. WeatherAPI terms state that plan rate limits apply and that overage charges may apply to applicable plans.

## Safeguards
- Manual `workflow_dispatch` only; defaults to **NO**.
- Requires selecting exact phrase `I_APPROVE_ONE_WEATHERAPI_REQUEST`.
- Exactly one code path capable of a single GET to `https://api.weatherapi.com/v1/current.json`.
- Fixed non-personal test location: Chicago; no user location is sent.
- Timeout 10 seconds; GitHub job timeout 2 minutes; no explicit retries.
- Redirect/endpoint changes fail closed by checking final scheme, host and path.
- Response limited to 32 KiB and never printed.
- Secret, URL, query string, headers and response body are never printed.
- Output is limited to PASS/HOLD plus sanitized category/status code.
- Response must pass existing location, timestamp freshness and temperature sanity validation.
- Forecast engine is never activated.

## Execution requirement
Do not run until the account owner has confirmed the specific WeatherAPI subscription/billing state and explicitly approves one call. A successful response demonstrates only bounded authentication and schema/freshness acceptance—not sports forecast accuracy or provider-wide entitlement.
