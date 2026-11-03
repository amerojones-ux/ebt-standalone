# Phase 60 — Carry signed execution authorization into evidence ledger v5

Status: **SAFE HOLD / OFFLINE**

Phase 59 proves that REVIEW_ONLY evidence can be reconstructed only from a provider run containing both the signed one-shot execution intent and the signed provider receipt chain. Phase 60 makes that authorization evidence durable.

## Evidence ledger schema v5

`config/provider_evidence.json` is now `schema_version: 5`.

A `live_auth_verified` record retains all schema-v4 provider, request-plan and reviewer provenance and additionally requires:

- `execution_intent_verified: true`
- `execution_intent_sha256`
- `execution_intent_file_sha256`
- `execution_intent_marker_sha256`
- `execution_intent_bundle_sha256`
- `execution_intent_attestation_id`
- `execution_intent_attestation_url`
- `execution_actor`
- `execution_actor_id`
- `execution_max_requests: 1`

The four authorization hashes must be valid SHA-256 values. The attestation URL must belong to the authoritative repository. Actor and actor ID must satisfy the same constrained GitHub identity format used by the signed intent contract. `execution_max_requests` must be the integer `1`; booleans, zero and values above one are rejected.

## REVIEW_ONLY candidate

A receipt-only candidate starts with:

- `execution_intent_verified: false`
- all execution-intent provenance fields null.

Only the full Phase-59 GitHub evidence ingester can bind the verified execution authorization into the candidate.

When REVIEW_ONLY is produced, the candidate checksum covers the complete authorization provenance.

## Reviewer behavior

The reviewer verifier independently requires the execution-intent authorization fields before a candidate can be approved.

An approved raw review decision copies the complete execution authorization into its proposed ledger record. The later signed GitHub reviewer-workflow package cannot omit or rewrite those fields without invalidating its decision/proposal checksums.

## Ledger behavior

Ledger schema v5 requires the complete execution authorization for `source_type: github_actions_receipt`.

It rejects:

- missing execution-intent verification;
- missing or malformed execution-intent hashes;
- malformed execution actor identity;
- invalid execution-intent attestation URL;
- any `execution_max_requests` value other than integer `1`;
- execution-intent fields on non-GitHub evidence.

## Audit result

The durable live-auth record now answers both:

1. **What exact request contract ran?** — via `request_plan_sha256`.
2. **Who explicitly authorized the one-shot run and under what signed intent?** — via the execution-intent provenance fields.

No provider request, secret access, ledger mutation, readiness mutation, forecast activation or wager action occurs in this phase.
