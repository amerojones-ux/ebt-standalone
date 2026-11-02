# Phase 54 — GitHub-native signed live-auth promotion preview workflow

Status: **PREPARED / DEFAULT NO / SAFE HOLD / NO STATE MUTATION**

Phase 53 requires a signed GitHub review package before live-auth evidence can enter ledger schema v3. Phase 54 makes the next dry-run step operationally reproducible inside GitHub Actions.

Workflow:

`.github/workflows/provider-live-auth-promotion-preview.yml`

## Default-deny invocation

The workflow is manual-only and requires:

`I_APPROVE_LIVE_AUTH_PROMOTION_PREVIEW`

The default confirmation is `NO`.

It runs only on `refs/heads/main`.

## Source review-run requirements

The supplied review workflow run ID must:

- be numeric;
- identify a completed `workflow_dispatch` run;
- originate from `main`;
- conclude `success`;
- use exactly:
  `.github/workflows/provider-live-auth-evidence-review.yml`;
- belong to the authoritative repository;
- have matching repository/head-repository identity;
- expose a valid source commit.

The workflow accepts exactly one unexpired artifact whose name matches:

`provider-live-auth-review-<source-probe-run-id>-<review-run-id>`

## Review-package reconstruction

The signed review package is downloaded from GitHub and processed through:

`provider_review_package_ingest_cli.py`

This produces a checksum-bound attested review decision containing both:

- provider-side signed provenance;
- reviewer-workflow signed provenance.

A raw review decision is not accepted.

## SAFE_HOLD promotion preview

The workflow then runs:

`provider_live_auth_promotion_preview_cli.py`

against the committed:

- `config/provider_readiness.json`;
- `config/provider_evidence.json`.

The resulting preview must satisfy all of:

- `VALID_LIVE_AUTH_PROMOTION_PREVIEW`;
- `GLOBAL_PROVIDER_GATE: SAFE_HOLD`;
- ledger writes disabled;
- readiness writes disabled;
- forecast activation disabled.

The preview changes only the in-memory provider field:

`live_auth_verified: false -> true`

No committed file is changed.

## Signed preview provenance

The generated `provider_live_auth_promotion_preview.json` is:

1. attested with the pinned `actions/attest`;
2. verified with `gh attestation verify`;
3. constrained to:
   - the authoritative repository;
   - the exact promotion-preview workflow;
   - `refs/heads/main`;
   - the exact workflow commit.

A sanitized verification marker records:

- promotion workflow run ID;
- source review workflow run ID;
- source provider probe run ID;
- preview internal checksum;
- exact preview-file checksum;
- `SAFE_HOLD` gate result;
- attestation ID and URL;
- exact signer workflow.

## Persisted preview package

Only these sanitized files are uploaded:

- `provider_attested_review_decision.json`;
- `provider_live_auth_promotion_preview.json`;
- `provider_live_auth_promotion_preview_attestation_verification.json`.

Retention is 7 days.

## Permission boundary

The workflow has:

- `contents: read`;
- `actions: read`;
- `id-token: write`;
- `attestations: write`;
- `artifact-metadata: write`.

It has no provider secret reference, no provider-network probe, no repository-content write permission, and no Actions write permission.

No provider request, credential read, ledger write, readiness write, forecast activation, or wager action occurs in this phase.
