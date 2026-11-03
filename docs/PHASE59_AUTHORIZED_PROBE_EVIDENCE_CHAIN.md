# Phase 59 — Authorized probe evidence chain required before REVIEW_ONLY

Status: **SAFE HOLD / OFFLINE**

Phase 59 repairs a concrete prepared-review defect and closes the gap between the signed pre-secret execution intent and the provider receipt evidence.

## Corrected review-path defect

Before this phase:

- `provider_github_artifact_ingest.py` required the receipt, receipt verification marker **and persisted receipt Sigstore bundle**;
- `provider_github_artifact_ingest_cli.py` and the GitHub review workflow still supplied only the receipt and marker.

Therefore the prepared review workflow could not successfully reconstruct current REVIEW_ONLY evidence.

Phase 59 aligns the CLI and workflow with the actual ingester contract.

## Full authorized source-run evidence

A provider probe source run must now supply six independently GitHub-metadata-bound artifacts:

1. sanitized provider receipt;
2. provider receipt attestation-verification marker;
3. exact provider receipt Sigstore bundle;
4. signed pre-secret execution-intent JSON;
5. execution-intent attestation-verification marker;
6. exact execution-intent Sigstore bundle.

Every artifact must:
- be unexpired;
- have an exact provider/run-specific artifact name;
- have a valid GitHub SHA-256 artifact digest;
- download to exactly the GitHub-declared size and digest;
- identify the same workflow run, source commit and repository.

## Execution-intent validation

The execution-intent JSON must pass the Phase 58 contract and match:

- provider;
- authoritative repository;
- source workflow run;
- source commit;
- exact provider probe signer workflow;
- canonical request-plan fingerprint;
- `max_requests: 1`.

The execution-intent verification marker additionally binds:

- GitHub actor and actor ID;
- intent checksum;
- exact intent-file SHA-256;
- canonical request-plan SHA-256;
- exact one-request limit;
- attestation ID/URL;
- exact exported bundle SHA-256;
- local-bundle + GitHub-API verification modes;
- pinned runner and toolchain fingerprint.

## Cross-chain requirements

Before a receipt can become REVIEW_ONLY, the ingester requires:

- receipt, receipt marker, receipt bundle, intent, intent marker and intent bundle to share the same GitHub run/commit/repository;
- intent JSON checksum = intent marker checksum reference;
- intent file hash = intent marker file-hash reference;
- intent request-plan fingerprint = intent marker fingerprint;
- intent request-plan fingerprint = receipt marker request-plan fingerprint;
- intent actor/actor ID = intent marker actor/actor ID;
- both intent sources to state exactly one request;
- execution-intent and receipt signer workflow to match;
- both persisted Sigstore bundle file hashes to match their verified markers.

Only after all checks pass can the existing checksum-bound REVIEW_ONLY candidate be created.

## Review workflow repair

`.github/workflows/provider-live-auth-evidence-review.yml` now resolves and downloads all six source-run artifacts for WeatherAPI, The Odds API and API-Sports.

The workflow passes all six metadata/ZIP pairs to the corrected GitHub evidence-ingestion CLI before any reviewer decision is emitted.

## Boundary

This phase proves that provider receipt evidence came from a run with a separately signed and verified one-shot authorization intent.

It does not execute a provider request, read a provider secret, write the evidence ledger/readiness configuration, activate forecasting, or place any wager.
