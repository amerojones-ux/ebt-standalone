# Phase 38 — Probe receipt to review-only evidence candidate

Status: **OFFLINE / NO AUTOMATIC PROMOTION**

WeatherAPI, The Odds API, and API-Sports have prepared sanitized live-probe receipt formats. Phase 37 requires reviewed evidence before any readiness flag may become true.

This phase connects those layers without creating an automatic promotion path.

`provider_receipt_review_candidate.py` accepts only:
- a supported provider receipt;
- a receipt that passes that provider's checksum/schema verifier;
- `status: PASS`;
- the exact provider-specific PASS category;
- a 40-character GitHub source commit;
- a numeric GitHub Actions run ID;
- the receipt's internal canonical-body `receipt_sha256`;
- a separate SHA-256 of the actual sanitized receipt file bytes (`artifact_sha256`).

It then emits a **REVIEW_ONLY** candidate for the single claim `live_auth_verified`.

The candidate explicitly sets:
- `reviewer_required: true`;
- `readiness_mutation_permitted: false`;
- `forecast_activation_permitted: false`.

It does not update `config/provider_readiness.json`, does not write `config/provider_evidence.json`, and cannot create a `VERIFIED` ledger record. An authorized review step is still required.

This preserves the distinction between:
1. a technically successful provider authentication probe;
2. reviewed evidence supporting a readiness claim;
3. actual provider/model readiness;
4. manual activation review.

No network request or secret access occurs in this phase.


## Phase 45 provenance clarification

The internal receipt checksum and the evidence-artifact checksum are intentionally distinct:

- `receipt_sha256` verifies the provider receipt's canonical JSON body according to its provider-specific schema.
- `artifact_sha256` verifies the exact sanitized receipt file bytes extracted from the GitHub Actions artifact.

The ZIP transport container itself is not mislabeled as either of these values. The receipt file hash is calculated after strict ZIP validation and before the REVIEW_ONLY candidate is built.
