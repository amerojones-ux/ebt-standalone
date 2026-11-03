# Phase 55 — Exact one-shot live-provider request plans

Status: **PREPARED_DEFAULT_DENY / NO LIVE REQUEST EXECUTED**

Phase 55 closes a request-surface drift found during the live-probe audit.

## Corrected defect

The WeatherAPI probe was still constructing:

`key=<secret>&q=Chicago&aqi=no`

while the intended strict request contract allowed only:

`key=<secret>&q=Chicago`

The undocumented-for-this-contract `aqi=no` parameter has been removed.

## Canonical request-plan module

`provider_live_request_plan.py` is now the single request-plan authority for:

- WeatherAPI
- The Odds API
- API-Sports

Each plan fixes:

- HTTPS scheme;
- exact host;
- exact path;
- GET method;
- exact query-key set;
- exact fixed query values;
- exact header-name set;
- credential transport location;
- 10-second timeout;
- exactly one request;
- zero retries;
- redirects disabled;
- maximum response body size.

Credential values are never included in the public plan representation.

## Exact request validation

Before the opener is invoked, every constructed request must pass validation that rejects:

- unsupported method;
- any request body;
- wrong scheme/host/path;
- URL userinfo;
- explicit port, including explicit `:443`;
- fragment;
- duplicate query keys;
- extra query keys;
- missing credential query/header;
- incorrect fixed query values;
- extra headers;
- missing or modified fixed headers.

The response URL is independently constrained to the approved scheme, host and path and rejects userinfo, explicit ports and fragments.

## Probe integration

All three live probe modules now construct requests only through the canonical builder.

The integration suite verifies:

- WeatherAPI uses exactly `key,q`, never `aqi`;
- The Odds API uses exactly `apiKey`;
- API-Sports sends no query string and only the documented application key header;
- each probe invokes its opener exactly once;
- each opener receives the canonical 10-second timeout;
- missing secrets prevent any opener call.

## Boundary

This phase does not authorize or perform a provider request. Existing workflow consent gates, signed provenance, cryptographic attestation verification, evidence ledger v3, reviewer workflow and SAFE_HOLD rules remain unchanged.
