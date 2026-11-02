# Phase 53 — Persist and independently bind the exact verified Sigstore bundle

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER EXECUTION**

Phase 51 verifies the exact local Sigstore bundle emitted by `actions/attest` and separately verifies through GitHub's attestation API. Phase 53 preserves that exact verified bundle as a third short-lived GitHub Actions artifact so post-run evidence review can independently bind to the same bytes.

## Workflow behavior

After both attestation verification passes succeed, each provider workflow:

1. copies the exact `steps.attest.outputs.bundle-path` file to a deterministic provider-specific filename;
2. verifies the exported file is non-empty;
3. calculates `attestation_bundle_sha256` from the exported file bytes;
4. records that hash in verification-marker schema v2;
5. uploads the exported bundle as a separate 7-day artifact.

Provider-specific bundle artifacts:

- WeatherAPI → `weatherapi-attestation-bundle-<run_id>`
- The Odds API → `theoddsapi-attestation-bundle-<run_id>`
- API-Sports → `apisports-attestation-bundle-<run_id>`

Only the exact JSON bundle file is uploaded. No wildcard/directory upload is used.

## Post-run ingestion

The preferred GitHub evidence path now requires three artifacts:

1. sanitized provider receipt;
2. attestation-verification marker;
3. exact attestation bundle.

For the bundle artifact, the ingester requires:

- GitHub artifact name/run/branch/commit metadata match;
- downloaded ZIP size and SHA-256 match GitHub artifact metadata;
- exactly one ZIP member;
- exact provider-specific filename;
- no directory, nested path, encryption, or symlink;
- bounded file size;
- valid UTF-8 JSON object;
- SHA-256 of extracted bundle bytes exactly equals the marker's `attestation_bundle_sha256`.

The receipt, marker, and bundle artifact metadata must all identify the same repository, workflow run and source commit.

## Evidence boundary

The final REVIEW_ONLY candidate is still derived only after:
- receipt verification;
- dual attestation verification;
- marker verification;
- exact persisted bundle verification.

The bundle artifact does not independently promote readiness and does not mutate the evidence ledger.

Committed state remains:
- provider reconciliation: SAFE_HOLD
- global provider/model gate: SAFE_HOLD
- live probes: PREPARED_DEFAULT_DENY
- forecasting: disabled
