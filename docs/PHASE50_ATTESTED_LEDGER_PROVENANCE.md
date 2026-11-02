# Phase 50 — Signed attestation provenance retained in evidence ledger v2

Status: **SAFE HOLD / OFFLINE**

Phase 49 requires cryptographic verification of a provider receipt attestation before a candidate can reach reviewer-eligible `REVIEW_ONLY`. Phase 50 ensures that provenance is not discarded when a reviewer approves the candidate.

## Evidence ledger schema v2

`config/provider_evidence.json` is now `schema_version: 2`.

For `source_type: github_actions_receipt`, a live-auth evidence record must preserve:

- `source_repository`
- `source_commit`
- `receipt_sha256` — provider receipt canonical-body checksum
- `artifact_sha256` — exact sanitized receipt-file bytes
- `attestation_marker_sha256` — exact verification-marker file bytes
- `attestation_id`
- `attestation_url`
- `signer_workflow`

These are in addition to the existing subject, claim, source reference, reviewer and review timestamp.

## Repository and signer policy

The live-auth evidence record is valid only when:

- source repository is exactly `amerojones-ux/ebt-standalone`;
- attestation URL belongs to that repository's GitHub attestation namespace;
- signer workflow is the exact provider-specific manual probe workflow;
- source commit is a 40-character Git SHA;
- all receipt/artifact/marker hashes are 64-character SHA-256 values.

The currently supported signed live-auth workflows are:

- WeatherAPI → `.github/workflows/weatherapi-live-probe.yml`
- The Odds API → `.github/workflows/theoddsapi-live-probe.yml`
- API-Sports → `.github/workflows/apisports-status-probe.yml`

Other providers remain fail-closed until they receive an equivalent signed probe workflow.

## Promotion chain

The full live-auth chain is now:

provider response
→ sanitized receipt
→ signed GitHub attestation
→ `gh attestation verify`
→ verification-marker artifact
→ same-run/same-commit GitHub artifact binding
→ checksum-bound `REVIEW_ONLY` candidate
→ explicit reviewer approval
→ signed-provenance ledger-record proposal
→ dry-run ledger preview
→ separate manual ledger/readiness change
→ global activation review

A reviewer-approved ledger proposal now retains the exact attestation identity that justified the approval.

## Non-GitHub evidence

Manual reviews and validation reports cannot contain attestation-specific fields. Validation reports continue to require their own artifact SHA-256.

The committed ledger still contains no verified live-auth records, so the expected platform state remains:

- evidence gate: PASS for current all-false readiness
- global provider/model gate: SAFE_HOLD
- live probes: PREPARED_DEFAULT_DENY

No provider network request, credential access, ledger mutation, readiness mutation or forecast activation occurs in this phase.


## Superseded ledger schema

Phase 53 supersedes evidence-ledger schema v2 with schema v3. Provider-side attestation provenance from Phase 50 remains required, and live-auth evidence now additionally requires the signed GitHub reviewer-workflow provenance documented in `docs/PHASE53_REVIEW_ATTESTATION_LEDGER_GATE.md`.
