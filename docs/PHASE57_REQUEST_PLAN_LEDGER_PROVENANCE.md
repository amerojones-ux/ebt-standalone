# Phase 57 — Carry request-plan provenance into REVIEW_ONLY candidates and evidence ledger v4

Status: **SAFE HOLD / OFFLINE**

Phase 56 binds the canonical one-shot provider request contract into the verified provider attestation marker. Phase 57 makes that request-plan fingerprint explicit throughout the downstream review and evidence chain.

## Evidence ledger schema v4

`config/provider_evidence.json` is now `schema_version: 4`.

For `source_type: github_actions_receipt`, the live-auth record now additionally requires:

`request_plan_sha256`

The evidence gate recomputes the canonical provider request-plan fingerprint and requires an exact match.

A correctly shaped 64-character but stale, cross-provider or otherwise incorrect fingerprint is invalid.

## Promotion chain

The verified request-plan fingerprint now flows through:

attestation verification marker
→ strict marker-artifact ingestion
→ GitHub three-artifact ingestion
→ checksum-bound REVIEW_ONLY candidate
→ review decision
→ signed reviewer package
→ ledger record proposal
→ evidence ledger v4
→ live-auth readiness promotion preview.

At each candidate/reviewer/ledger boundary, the canonical fingerprint is independently checked against `provider_live_request_plan.request_plan_sha256(provider)`.

## Candidate behavior

A receipt-only candidate has:

`request_plan_sha256: null`

It cannot be reviewer-eligible.

Only after the verified provider attestation marker is ingested and its plan fingerprint matches the repository's canonical request plan can the candidate become:

`REVIEW_ONLY`

with a non-null canonical `request_plan_sha256`.

That field is included in the candidate checksum.

## Reviewer and ledger behavior

The raw review decision copies the verified plan fingerprint into its ledger proposal.

Ledger schema v4 requires the fingerprint and rejects:
- a missing value;
- malformed SHA-256;
- a fingerprint for another provider;
- a fingerprint from an older/different request contract.

The signed reviewer-workflow provenance required by schema v3 remains required unchanged.

## Boundary

This phase improves auditability and prevents request-contract evidence drift. It does not authorize or execute a provider request and does not write readiness, evidence or forecast state.
