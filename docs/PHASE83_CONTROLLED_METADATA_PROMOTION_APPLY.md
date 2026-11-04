# Phase 83 — Controlled provider account-metadata promotion apply

Status: **ISOLATED_BRANCH_APPLY_ONLY / NO DIRECT MAIN WRITE / NO PROVIDER REQUEST**

Phase 83 is the controlled apply stage for source-verified provider account
metadata.

It may create a new isolated GitHub branch containing exactly two metadata
files. It may not write directly to protected main, open or merge a pull
request, contact a provider, enable forecasting, enable model evidence, or
authorize a provider request.

## Required chain

Phase 83 consumes only a successful signed Phase 82 promotion preview.

The complete chain is:

1. Phase 80 — signed account-metadata claim.
2. Phase 81 — provider-source verification review.
3. Phase 82 — current-state drift-checked promotion preview.
4. Phase 83 — current-state drift-checked isolated-branch apply.
5. External protected PR review and required CI.
6. Separate provider-specific live-auth implementation and fresh request
   authorization before any provider network call.

## Workflow

`.github/workflows/provider-account-metadata-promotion-apply.yml`

Manual confirmation phrase:

`I_APPROVE_ACCOUNT_METADATA_PROMOTION_APPLY`

The workflow requires:

- manual `workflow_dispatch`;
- run attempt 1;
- protected `main`;
- exact Phase 82 preview workflow run ID;
- current main to remain exactly at the workflow source SHA before branch
  creation; and
- successful verification of every signed artifact in the upstream chain.

## Phase 82 run binding

The apply workflow requires the source preview run to be:

- `workflow_dispatch`;
- run attempt 1;
- on `main`;
- completed successfully;
- from
  `.github/workflows/provider-account-metadata-promotion-preview.yml`;
- from the same repository/head repository; and
- bound to a valid 40-character commit.

The expected preview artifact name is:

`provider-account-metadata-promotion-preview-<source_review_run>-<preview_run>`

Exactly one unexpired matching artifact is permitted.

## Strict preview package ingestion

The Phase 82 ZIP must contain exactly five files:

- `account_metadata_claim.json`
- `account_metadata_source_review_decision.json`
- `account_metadata_source_review_attestation.json`
- `account_metadata_promotion_preview.json`
- `account_metadata_promotion_preview_attestation.json`

The workflow rejects:

- missing or extra members;
- nested paths;
- encrypted members;
- symlinks;
- oversized members;
- malformed ZIPs; and
- duplicate/missing matching artifacts.

## Full provenance re-verification

Before apply, Phase 83 re-verifies:

- Phase 80 claim schema/checksum;
- Phase 81 source-review decision schema/checksum;
- Phase 81 decision = APPROVE;
- Phase 82 promotion-preview schema/checksum;
- claim run and checksum bindings;
- Phase 81 review-run binding;
- Phase 81 review-decision checksum binding;
- Phase 82 attestation marker run/commit/ref/signer binding; and
- the Phase 82 GitHub attestation itself against the exact preview workflow and
  source digest.

## Current-state reconstruction

The workflow then calls
`provider_account_metadata_promotion_apply.py`.

The apply builder rebuilds the Phase 82 preview again from current committed
main state.

The rebuilt preview must be byte-for-byte logically equal to the signed Phase
82 preview.

Any state drift forces failure.

Examples of drift include:

- a changed provider product or plan;
- a changed account-evidence flag;
- a different quota or access-level assumption;
- a changed endpoint or host;
- another metadata promotion already having been applied; or
- any cross-provider metadata change.

## Mutation scope

A valid apply may propose changes only to:

1. `config/provider_account_evidence.json`
2. exactly one selected provider config:

   - SportsDataIO:
     `config/sportsdataio_access.json`
   - Sportradar:
     `config/sportradar_nfl_auth.json`
   - RapidAPI:
     `config/rapidapi_routing.json`

Any change to another provider's operational config is forbidden.

Any change to another provider's account-evidence entry is forbidden.

A no-op/already-applied promotion is rejected.

## Safety invariants

The target account-evidence entry must keep:

- `live_request_permitted=false`
- `model_evidence_allowed=false`

The target operational provider config must keep:

- `network_enabled=false`
- `forecast_enabled=false`

The apply manifest requires:

- `isolated_branch_write_permitted=true`
- `main_write_permitted=false`
- `provider_network_request_permitted=false`
- `forecast_activation_permitted=false`
- `model_evidence_allowed=false`

Phase 83 does not modify:

- `config/provider_readiness.json`
- `config/provider_evidence.json`

Thus a metadata promotion cannot silently become live-auth verification or
forecast readiness.

## Exact file-byte binding

The apply manifest contains SHA-256 hashes of the exact serialized bytes that
may be written to:

- `config/provider_account_evidence.json`
- the selected provider config

The workflow regenerates those files and verifies their SHA-256 hashes against
the manifest before branch creation.

The manifest itself is checksum-bound, self-verified, GitHub-attested and
verified twice:

1. locally using the exact attestation bundle;
2. independently through GitHub attestation verification.

## Branch-only write

Immediately before creating the promotion branch, the workflow fetches the live
`main` ref and requires it to equal the workflow's immutable source SHA.

The branch name is:

`promotion/<provider>-account-metadata-<preview_run>-<apply_run>`

The branch begins at that exact main commit.

Only the two allowed files are written to that branch.

The workflow uses the current base blob SHAs and verifies GitHub's returned Git
blob SHA for each write against `git hash-object` of the generated content.

This ensures the repository bytes created on the branch are exactly the bytes
covered by the apply manifest.

## No automatic pull request

Phase 83 intentionally does not open or merge a pull request.

An authorized external GitHub client must:

1. inspect the exact branch diff;
2. confirm only the two expected files changed;
3. open the PR;
4. allow both required protected validations to run; and
5. merge only if every gate remains green.

The protected checks remain:

- `validation (3.11)`
- `validation (3.13)`

## Apply evidence

The workflow retains for seven days:

- `account_metadata_promotion_apply_manifest.json`
- generated account-evidence file;
- generated selected-provider config

No credentials are included.

## Provider request boundary

Even after a Phase 83 branch is reviewed and merged, that does not authorize a
provider request.

A remaining provider may only advance to network testing after its exact
account metadata is persisted, a hardened one-shot provider workflow is
installed and reviewed, and a fresh provider-specific request authorization is
given.

Global provider/model state remains `SAFE_HOLD`.
