# Phase 51 — Non-mutating live-auth promotion preview

Status: **SAFE HOLD / OFFLINE**

Phase 50 preserves the complete signed-provenance chain in evidence ledger v3. Phase 51 adds a deterministic dry-run promotion package for the next step: setting exactly one provider readiness flag, `live_auth_verified=true`, after an approved attested live-auth evidence record.

## Inputs

The preview requires:
- current committed readiness config;
- current evidence ledger v3;
- an attested GitHub APPROVE review decision;
- trusted UTC time.

The attested review decision must contain both provider-receipt provenance and the signed GitHub reviewer-workflow provenance required by ledger schema v3.

## Preview behavior

The tool first builds the existing non-mutating ledger preview. It then deep-copies the readiness configuration and changes exactly one field for the reviewed provider:

`live_auth_verified: false -> true`

It refuses to proceed if:
- the current readiness config is invalid;
- the review decision is not approved;
- the decision is not for `live_auth_verified`;
- the provider is missing;
- `live_auth_verified` is already true;
- any readiness field other than `live_auth_verified` changes;
- the proposed readiness config is invalid;
- the proposed true readiness claim is not supported by the preview evidence ledger;
- the global provider/model gate would return anything other than `SAFE_HOLD`.

## Output

A successful result is:

`VALID_LIVE_AUTH_PROMOTION_PREVIEW`

The package includes:
- provider and claim;
- review-decision checksum;
- preview evidence ledger;
- preview readiness config;
- resulting global provider gate;
- SHA-256 checksum over the complete preview body.

It explicitly states:
- ledger writes disabled;
- readiness writes disabled;
- forecast activation disabled.

## Why SAFE_HOLD is mandatory

Live authentication proves only that one controlled provider request authenticated and produced the expected sanitized response schema. It does **not** prove:
- account entitlement for production data;
- identity/roster correctness;
- data freshness across production feeds;
- model-evidence suitability;
- source-provenance completeness;
- historical calibration;
- dependence/correlation calibration;
- required-provider selection.

Therefore a live-auth promotion preview must never itself make the platform activation-eligible.

No network request, credential read, ledger mutation, readiness mutation, or forecast activation occurs in this phase.
