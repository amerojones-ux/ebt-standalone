# Phase 37 — Evidence ledger required for readiness promotion

Status: **SAFE HOLD / OFFLINE**

Black Diamond now separates two evidence responsibilities:

1. `extensions/provider_evidence_gate.py` validates provider receipt completeness/freshness for review-only use.
2. `provider_readiness_evidence_gate.py` controls whether repository readiness booleans may be promoted.

This phase does **not** replace or weaken the existing receipt-freshness engine.

## Readiness claims covered
For every provider:
- live authentication;
- entitlement;
- identity;
- freshness;
- model-evidence eligibility.

For model-level certification:
- source provenance;
- roster/injury identity;
- historical calibration;
- joint dependence/correlation validation.

A readiness flag may be `true` only when `config/provider_evidence.json` contains a matching reviewed record.

## Evidence-record requirements
Each record requires:
- `status: VERIFIED`;
- source type: `github_actions_receipt`, `manual_review`, or `validation_report`;
- non-empty reference;
- timezone-aware review timestamp;
- named reviewer.

GitHub Actions receipt records additionally require:
- exact 40-character source commit SHA;
- 64-character artifact SHA-256 checksum.

These fields impose provenance discipline. They are not a cryptographic signature of reviewer identity.

## Activation behavior
`provider_activation_gate.activation_eligible()` now defaults to evidence failure. The caller must explicitly pass `evidence_ok=True`, and the normal CLI calculates that only through `provider_readiness_evidence_gate.evidence_supports_readiness()`.

The committed ledger contains no verified records, matching the current all-false live/model readiness state. Therefore expected outputs remain:

- `EVIDENCE_GATE: PASS`
- `GLOBAL_PROVIDER_GATE: SAFE_HOLD`

No provider network, secret, quota, or wager action is touched by this phase.
