# Phase 56 — Bind the exact live request plan into signed provider evidence

Status: **PREPARED_DEFAULT_DENY / NO LIVE REQUEST EXECUTED**

Phase 55 made the outbound request surface exact. Phase 56 binds that request contract into the probe evidence itself.

## Deterministic request-plan fingerprint

`provider_live_request_plan.request_plan_sha256(provider)` computes SHA-256 over a canonical public representation of the provider's live request plan.

The fingerprint covers:

- provider identity;
- HTTPS scheme;
- exact host;
- exact path;
- GET method;
- exact query-key set;
- fixed query values;
- exact header-name set;
- timeout;
- maximum request count;
- redirect policy;
- retry count;
- maximum response body size.

Credential values are not included.

## Attestation verification marker schema v4

The provider attestation-verification marker is upgraded from schema v3 to schema v4 and now includes:

`request_plan_sha256`

The marker validator recomputes the expected fingerprint from the repository's canonical request-plan module and requires an exact match.

Therefore an otherwise valid marker is rejected if:

- the request plan changed after the run;
- a marker from another provider is substituted;
- the plan fingerprint is altered;
- a schema-v3 marker is supplied.

The marker's own canonical SHA-256 also covers the new field.

## Workflow enforcement

WeatherAPI, The Odds API and API-Sports all write the canonical request-plan fingerprint into their verified marker after the receipt attestation has passed both:

- local exported-bundle verification;
- GitHub API attestation verification.

The probe readiness registry now requires the schema-v4 marker body and request-plan fingerprint binding for `PREPARED_DEFAULT_DENY`.

## Tests

The test suite covers:

- deterministic fingerprint stability;
- provider-specific fingerprints;
- valid schema-v4 marker;
- schema-v3 rejection;
- wrong plan fingerprint rejection;
- cross-provider fingerprint rejection;
- marker checksum tamper rejection;
- workflow/registry enforcement of the fingerprint field.

## Boundary

This phase binds evidence to the exact approved request contract. It does not authorize or execute any provider network request. Existing consent phrases, secret isolation, one-request limits, no-retry/no-redirect behavior, evidence ledger v3, reviewer attestation, promotion preview and global `SAFE_HOLD` remain unchanged.
