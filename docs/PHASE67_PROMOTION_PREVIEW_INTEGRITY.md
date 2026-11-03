# Phase 67 — Promotion-preview execution and attestation integrity

Status: **SAFE HOLD / OFFLINE**

Phase 67 hardens the non-mutating provider live-auth promotion-preview workflow and makes its attestation verification marker independently machine-verifiable.

## Promotion workflow execution controls

The promotion-preview workflow now requires:

- `github.run_attempt == 1`
- `github.ref_protected == true`
- `github.ref == 'refs/heads/main'`
- the exact `I_APPROVE_LIVE_AUTH_PROMOTION_PREVIEW` authorization phrase

Promotion-preview executions are serialized through:

`ebt-live-auth-promotion-preview`

with `cancel-in-progress: false`.

## Immutable promotion source

The workflow checks out:

`ref: ${{ github.sha }}`

and verifies:

- `git rev-parse HEAD == GITHUB_SHA`
- a clean working tree

before reading the committed readiness/evidence files or constructing a preview.

The reviewed upstream workflow must already satisfy the Phase 66 first-attempt requirement.

## Promotion attestation marker v2

The promotion-preview attestation verification marker is upgraded to schema v2 and binds:

- promotion workflow run ID;
- `promotion_workflow_run_attempt: 1`;
- upstream review workflow run ID;
- original source probe run ID;
- exact source commit;
- exact signer workflow;
- preview internal SHA-256;
- preview file SHA-256;
- `SAFE_HOLD` as the global provider gate;
- attestation ID and GitHub attestation URL.

## Independent marker verifier

`provider_promotion_preview_attestation_marker.py` now validates the marker using an exact-field allowlist and canonical checksum.

The workflow invokes this verifier before setting `preview_attestation_verified=1`.

A marker is rejected if any of the following drift:

- workflow attempt;
- current run ID;
- review run ID;
- source probe run ID;
- source commit/ref;
- signer workflow;
- preview filename or hashes;
- global gate away from `SAFE_HOLD`;
- attestation identity/URL;
- verification tool;
- canonical marker checksum.

Regression tests exercise the valid path and adversarial mutations.

## Boundary

The promotion preview remains non-mutating:

- evidence-ledger writes: forbidden;
- readiness writes: forbidden;
- forecast activation: forbidden;
- provider network calls: none;
- provider secret access: none;
- wager execution: none.

Global state remains `SAFE_HOLD`.
