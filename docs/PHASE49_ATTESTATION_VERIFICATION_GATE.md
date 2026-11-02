# Phase 49 — Cryptographic attestation verification required before review

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER EXECUTION**

Phase 48 generated signed provenance attestations for sanitized provider receipts. Phase 49 enforces GitHub's security requirement that those attestations be **verified**, not merely generated.

## In-workflow verification

After a receipt passes its provider-specific checksum/schema verifier and the pinned `actions/attest` step succeeds, the workflow runs:

`gh attestation verify`

against the exact receipt file with all of the following policy constraints:

- repository: `$GITHUB_REPOSITORY`
- signer workflow: the exact provider probe workflow path
- source ref: `refs/heads/main`
- source digest: `$GITHUB_SHA`
- default SLSA provenance predicate verification

A verification failure prevents an attestation-verification marker from being created.

## Verification marker

Successful verification creates one sanitized JSON marker containing:

- provider
- repository
- workflow run ID
- source commit
- source ref
- exact signer workflow path
- attestation ID and GitHub attestation URL
- exact receipt filename
- verification tool identifier
- SHA-256 checksum over the canonical marker body

The marker is uploaded as a separate 7-day artifact. It never contains provider credentials, response bodies, request headers, quota balances, or account data.

## Candidate state machine

A receipt artifact alone now produces only:

`REVIEW_ONLY_PENDING_ATTESTATION`

It has:
- GitHub receipt/artifact metadata binding;
- receipt checksum;
- receipt-file hash;
- `attestation_verified: false`.

The preferred GitHub ingestion path requires both:

1. the sanitized receipt artifact;
2. the attestation-verification marker artifact.

Their GitHub artifact metadata must identify the same repository, workflow run, `main` branch and source commit. The marker content must pass its checksum/schema verifier and match the exact provider/repository/run/commit/signer/receipt identity.

Only then is the candidate rebound to:

`REVIEW_ONLY`

with:
- `attestation_verified: true`;
- SHA-256 of the exact verification-marker file bytes bound into the candidate checksum.

Reviewer decisions reject candidates still pending attestation.

## CI enforcement

The normal security tests and `PREPARED_DEFAULT_DENY` registry now require:

- pinned `actions/attest`;
- exact receipt subject;
- explicit `gh attestation verify`;
- repository constraint;
- signer-workflow constraint;
- `refs/heads/main` constraint;
- source-digest constraint;
- separate verification-marker artifact.

No provider request is executed, and no ledger/readiness/forecast mutation occurs in this phase.
