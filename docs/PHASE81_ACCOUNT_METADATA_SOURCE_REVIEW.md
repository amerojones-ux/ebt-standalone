# Phase 81 — Provider account-metadata source review

Status: **SOURCE_REVIEW_ONLY / NO METADATA WRITE / NO PROVIDER REQUEST**

Phase 81 introduces the reviewer layer for Phase 80 attested account-metadata
claims.

The core distinction is preserved:

1. Phase 80 proves who submitted an account-metadata claim and exactly what was
   submitted.
2. Phase 81 records whether a GitHub reviewer checked that claim against the
   underlying provider portal/support source and whether it matched.
3. A later controlled apply phase is still required before account evidence or
   operational provider configuration may change.

## Workflow

`.github/workflows/provider-account-metadata-source-review.yml`

Supported providers:

- SportsDataIO
- Sportradar
- RapidAPI

Inputs:

- provider;
- completed Phase 80 claim workflow run ID;
- APPROVE / REJECT / HOLD;
- exact nonsecret source reference from the signed claim; and
- explicit approval phrase for APPROVE.

APPROVE requires:

`I_APPROVE_ACCOUNT_METADATA_SOURCE_VERIFICATION`

HOLD does not execute the review job.

## Source-run binding

The workflow resolves the exact expected Phase 80 source workflow and artifact
name from the selected provider.

It requires the source run to be:

- `workflow_dispatch`;
- run attempt 1;
- protected `main`;
- completed successfully;
- from the expected provider-specific claim workflow;
- from the same repository/head repository; and
- bound to a valid 40-character commit.

The exact claim artifact must be present once and unexpired.

## Strict artifact ingestion

The Phase 80 claim ZIP must contain exactly:

- `account_metadata_claim.json`
- `account_metadata_claim_attestation.json`

The workflow rejects:

- unexpected files;
- nested paths;
- encrypted ZIP members;
- symlinks;
- invalid/oversized members; and
- malformed ZIPs.

## Original claim re-verification

Before a source-review decision is created, Phase 81 verifies:

- Phase 80 claim schema/checksum;
- provider identity;
- source claim run ID;
- source commit;
- exact source reference;
- Phase 80 attestation marker status;
- marker run/commit/ref/signer binding; and
- the original GitHub attestation itself against the exact provider-specific
  Phase 80 signer workflow and source digest.

Thus a reviewer cannot approve a different claim, a copied artifact from a
different provider, or an artifact detached from its original run.

## Decision contract

`provider_account_metadata_source_review.py` produces checksum-bound review
decisions.

APPROVE means the reviewer asserts:

- the underlying provider portal/support source was reviewed;
- it matches the signed Phase 80 claim; and
- the claim may advance to a later metadata-promotion stage.

APPROVE records:

- `provider_source_reviewed=true`
- `provider_source_match=true`
- `claim_verified_against_provider_source=true`
- the exact approved Phase 79 transition proposal

REJECT records:

- `provider_source_reviewed=true`
- `provider_source_match=false`
- `claim_verified_against_provider_source=false`
- no approved transition

Both decisions remain non-mutating.

## Safety invariants

Even an approved source-review decision requires:

- `metadata_promotion_permitted=false`
- `network_request_permitted=false`
- `forecast_activation_permitted=false`
- `model_evidence_allowed=false`

Phase 81 never writes:

- `config/provider_account_evidence.json`
- operational provider config files;
- `config/provider_readiness.json`

It does not create branches, commits or pull requests.

## Reviewer provenance

Reviewer identity is derived from:

- `github.actor`
- `github.actor_id`

The decision is self-verified before attestation.

GitHub then attests the decision. The workflow independently verifies that
attestation against:

- this repository;
- the Phase 81 signer workflow;
- protected `main`; and
- the exact Phase 81 source digest.

The sanitized four-file review package is retained for seven days.

## Next layer

Only an APPROVE decision from Phase 81 may be considered by a future controlled
metadata-promotion preview/apply engine.

That later engine must:

- ingest the signed Phase 81 package strictly;
- rebuild the transition against current committed account/config state;
- reject drift;
- keep provider networking disabled;
- keep forecasting disabled;
- create an isolated branch only;
- require protected CI and PR review before merge.

Even after metadata promotion, a separate provider-specific one-shot workflow
and fresh exact request authorization remain required before any provider call.

Global provider/model state remains `SAFE_HOLD`.
