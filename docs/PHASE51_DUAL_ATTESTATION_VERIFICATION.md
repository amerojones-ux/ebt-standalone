# Phase 51 — Dual attestation verification: exact bundle + GitHub API

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER EXECUTION**

Phase 49 required `gh attestation verify` before a receipt could become reviewer-eligible. Phase 51 strengthens that verification so a pre-existing matching attestation cannot accidentally satisfy the same policy.

## Exact attestation binding

The pinned `actions/attest` step exposes the exact local Sigstore bundle it just created through `steps.attest.outputs.bundle-path`.

Each provider workflow now performs **two independent verification passes** against the same sanitized receipt:

1. **Exact local bundle verification**
   - `gh attestation verify "$RECEIPT_FILE" --bundle "$ATTESTATION_BUNDLE_PATH" ...`
   - proves the exact bundle emitted by the current `actions/attest` step verifies the receipt under the expected repository/signer/ref/commit policy.

2. **GitHub API verification**
   - the same policy is re-run without `--bundle`;
   - confirms a matching attestation is discoverable through GitHub's repository-linked attestation API.

Both passes enforce:
- exact repository;
- exact provider signer workflow;
- `refs/heads/main`;
- exact `$GITHUB_SHA`;
- default SLSA provenance predicate verification.

A failure in either pass prevents creation of the verification marker.

## Verification marker schema v2

The sanitized marker is now `schema_version: 2` and additionally binds:

- `attestation_bundle_sha256` — SHA-256 of the exact local Sigstore bundle produced by `actions/attest`;
- `verification_modes: ["local_bundle", "github_api"]`.

The marker's own SHA-256 covers both fields.

The downstream marker validator rejects:
- schema v1 markers;
- missing/invalid bundle hash;
- missing, reordered, or weakened verification modes;
- wrong provider/repository/run/commit/ref/signer/receipt identity;
- invalid attestation ID/URL;
- marker checksum mismatch.

## Why both checks

Local `--bundle` verification binds the check to the exact attestation generated in the current run. GitHub-API verification independently confirms repository association/discoverability. Together they are stronger than either check alone.

The final evidence ledger remains schema v2 because it already binds the exact verification-marker file SHA-256 and the GitHub attestation identity. The new bundle hash is therefore transitively bound by the marker without another ledger-schema migration.

No provider request, secret access, evidence promotion, readiness mutation, or forecast activation occurs in this phase.
