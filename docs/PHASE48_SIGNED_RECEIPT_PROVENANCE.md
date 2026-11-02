# Phase 48 — Signed provenance attestations for sanitized probe receipts

Status: **PREPARED / NO LIVE PROVIDER EXECUTION**

The repository is public and GitHub supports artifact attestations for public repositories. The three prepared live-auth workflows now generate a signed provenance attestation for the sanitized receipt file whenever that receipt passes its provider-specific checksum/schema verification.

## Action and permissions

The workflows pin the official `actions/attest` v4.2.2 release to the immutable commit:

`1e69f48acb82d1966a394da916b4c1698aa569d6`

The workflow permission set is explicitly limited to:

- `contents: read`
- `id-token: write`
- `attestations: write`
- `artifact-metadata: write`

No package, repository-content, issue, pull-request, deployment, or secret write permission is granted.

## Attestation gate

The probe step writes only:

`receipt_verified=1`

after the receipt has passed its provider-specific checksum/schema verifier.

The attestation step uses:

`if: always() && steps.probe.outputs.receipt_verified == '1'`

Therefore:
- a valid PASS receipt can be attested;
- a valid sanitized HOLD receipt can also be attested even though the probe job ultimately fails;
- an absent or invalid receipt is never attested.

Only the exact sanitized receipt JSON path is the attestation subject.

## Security improvement

The receipt's internal SHA-256 checksum is still only an integrity checksum and is not a signature.

GitHub artifact attestation adds a separate signed provenance layer using the workflow identity and short-lived signing credentials. This is stronger evidence of where and how the receipt artifact was produced.

Attestation creation does not promote provider readiness, write the evidence ledger, or activate forecasting. The normal review/evidence chain still applies.

## CI enforcement

Both:
- `tests/test_live_probe_security_invariants.py`
- `provider_probe_readiness_registry.py`

now require the exact pinned attestation action, required permission set, verified-receipt gate, and exact receipt subject path.

The expected live-probe registry state remains:

`PREPARED_DEFAULT_DENY`

No provider request is executed by this phase.
