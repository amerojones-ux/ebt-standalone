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


## Schema v2 update

Phase 50 supersedes the initial ledger record shape with `schema_version: 2` for live-auth evidence. GitHub Actions receipt records now require the signed-attestation provenance fields documented in `docs/PHASE50_ATTESTED_LEDGER_PROVENANCE.md`. The original evidence-source and claim-binding principles remain unchanged.


## Schema v3 update

Phase 53 supersedes schema v2 with `schema_version: 3` for live-auth evidence. In addition to provider-side signed provenance, live-auth records now require GitHub-actor reviewer identity and the signed/verified review-workflow provenance chain. Raw review decisions are no longer sufficient for ledger preview or readiness promotion.
