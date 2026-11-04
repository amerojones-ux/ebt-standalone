# Phase 82 — Drift-checked provider account-metadata promotion preview

Status: **PREVIEW_ONLY / NO METADATA WRITE / NO PROVIDER REQUEST**

Phase 82 upgrades the Phase 80 claim schema before first use and adds a
non-mutating promotion preview that rebuilds source-approved metadata against
current committed state.

No Phase 80/81 metadata workflow had run before this schema upgrade, so there
are no historical metadata artifacts requiring backward compatibility.

## Claim schema v2

Phase 80 claims now include checksum-bound:

`submitted_facts`

The facts are sanitized provider-specific metadata only. They contain no API
keys, tokens, passwords, credentials, account IDs or secret values.

The claim verifier requires the exact provider-specific fact field set.

This is necessary because a later promotion must be rebuilt from the original
facts rather than trusting a stale generated transition.

## Promotion preview contract

`provider_account_metadata_promotion_preview.py`

requires:

- a valid Phase 80 schema-v2 claim;
- a valid Phase 81 source-review decision;
- Phase 81 decision = APPROVE;
- exact provider binding;
- exact claim run ID binding;
- exact claim checksum binding;
- exact claim commit binding;
- source type/reference binding; and
- the Phase 81 approved transition to equal the original signed claim
  transition.

The preview also binds:

- exact Phase 81 source-review run ID;
- exact Phase 81 source-review commit; and
- Phase 81 decision checksum.

## Current-state drift reconstruction

The preview does not copy the old transition into the candidate state.

It calls the Phase 79 transition engine again using:

- the signed `submitted_facts`;
- current committed `config/provider_account_evidence.json`; and
- current committed unresolved-provider configs.

The rebuilt transition must exactly equal:

1. the original Phase 80 signed claim transition; and
2. the Phase 81 source-approved transition.

Any account/config drift causes HOLD.

This protects against promoting metadata after another change has altered the
provider state, quota assumptions, route, access level or account-evidence
registry.

## Workflow

`.github/workflows/provider-account-metadata-promotion-preview.yml`

The workflow requires:

- manual `workflow_dispatch`;
- first attempt only;
- protected `main`;
- exact Phase 81 review run ID; and
- `I_APPROVE_ACCOUNT_METADATA_PROMOTION_PREVIEW`.

It validates the Phase 81 run as:

- workflow_dispatch;
- run attempt 1;
- main;
- completed successfully;
- exact source-review workflow; and
- same repository/head repository.

## Strict Phase 81 package ingestion

The source-review artifact must match:

`provider-account-metadata-source-review-<claim_run>-<review_run>`

and must contain exactly four files:

- `account_metadata_claim.json`
- `account_metadata_claim_attestation.json`
- `account_metadata_source_review_decision.json`
- `account_metadata_source_review_attestation.json`

Nested paths, encryption, symlinks, unexpected files and oversized members are
rejected.

## Source-review re-verification

Before rebuilding, Phase 82 re-verifies:

- claim schema/checksum;
- Phase 81 decision schema/checksum;
- APPROVE status;
- claim run/checksum/commit/provider/reference bindings;
- approved transition equality;
- Phase 81 attestation marker run/commit/ref/signer binding; and
- the Phase 81 GitHub attestation itself against the exact source-review
  workflow and source digest.

## Preview output

A valid preview contains:

- provider;
- source claim run/checksum;
- source-review run/commit/decision checksum;
- source reference/type;
- current-state checksum;
- rebuilt-transition checksum;
- complete candidate account-evidence registry; and
- complete candidate unresolved-provider configs.

The preview remains:

- `metadata_write_permitted=false`
- `network_request_permitted=false`
- `forecast_activation_permitted=false`
- `model_evidence_allowed=false`

The preview is checksum-bound, self-verified, attested by GitHub, independently
re-verified, and uploaded in a seven-day sanitized package.

## Next layer

A controlled apply stage may consume only a valid signed Phase 82 preview.

That apply must rebuild the preview again against the then-current main state,
reject drift, and create an isolated branch containing only:

- `config/provider_account_evidence.json`; and
- the one applicable provider operational config.

It must not enable provider networking, forecasting or model evidence and must
not merge directly to main.

A protected PR and both required validation jobs remain mandatory.

Even after metadata promotion, a separate hardened provider live-auth workflow
and fresh provider-specific request authorization are still required before any
provider request.

Global provider/model state remains `SAFE_HOLD`.
