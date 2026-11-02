# Phase 55 — Bind the live-probe toolchain fingerprint into verification evidence

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER EXECUTION**

Phase 54 pins the runner/Python environment and requires a GitHub CLI capability preflight before any provider request can execute. Phase 55 carries that execution environment into the already-required attestation-verification marker so post-run evidence can be audited against the exact toolchain that performed verification.

## Toolchain outputs

The preflight now records:

- exact Python runtime version;
- exact GitHub CLI version;
- successful capability verification for the required attestation flags.

The workflow still requires Python major/minor 3.13 before emitting `toolchain_verified=1`.

## Verification marker schema v3

Marker schema v3 adds:

- `runner_label: ubuntu-24.04`
- `python_version`
- `gh_version`
- `setup_python_sha`
- `required_attestation_flags`

The required flags are exactly:

- `--bundle`
- `--repo`
- `--signer-workflow`
- `--source-ref`
- `--source-digest`
- `--format`

The pinned setup-python commit is:

`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`

All fields are included in the marker's canonical-body SHA-256.

## Validation policy

The marker validator rejects:

- schema versions other than 3;
- runner labels other than `ubuntu-24.04`;
- Python versions outside 3.13.x;
- malformed GitHub CLI versions;
- setup-python commit drift;
- missing, reordered, or weakened attestation flag lists;
- any existing repository/run/commit/signer/attestation/bundle mismatch.

## Evidence chain

The post-run path now binds:

pinned runner + Python
→ GitHub CLI capability preflight
→ one provider request
→ sanitized receipt
→ signed attestation
→ exact-bundle verification
→ GitHub-API verification
→ persisted exact bundle
→ marker schema v3 with toolchain fingerprint
→ GitHub artifact transport verification
→ REVIEW_ONLY candidate
→ reviewer decision
→ evidence ledger v2.

The evidence ledger does not require another schema bump because it already retains the exact marker-file SHA-256. The toolchain fingerprint is therefore transitively bound by that ledger evidence.

No provider request, secret access, evidence promotion, readiness mutation, or forecasting activation occurs in this phase.
