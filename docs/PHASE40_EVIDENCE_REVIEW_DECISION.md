# Phase 40 — Explicit reviewer decision and ledger-record proposal

Status: **SAFE HOLD / OFFLINE**

A successful provider probe now follows this controlled path:

1. provider PASS receipt;
2. checksum-bound `REVIEW_ONLY` candidate;
3. explicit reviewer APPROVE or REJECT decision;
4. optional **ledger-record proposal**;
5. separate manual ledger/readiness change;
6. global activation gate.

## Candidate integrity

Phase 38 review candidates now include `candidate_sha256`, calculated over the canonical candidate body. Phase 40 verifies that checksum before accepting a reviewer decision.

## Reviewer decision

`provider_evidence_review_decision.py` requires:
- verified candidate checksum;
- explicit `APPROVE` or `REJECT`;
- named reviewer;
- timezone-aware review timestamp;
- review timestamp not later than trusted runtime time.

A rejection produces no ledger record.

Approval produces a `ledger_record_proposal` matching the claim-bound live-auth evidence schema, but the result explicitly states:
- `ledger_mutation_permitted: false`
- `readiness_mutation_permitted: false`
- `forecast_activation_permitted: false`

The tool does not edit `config/provider_evidence.json` or `config/provider_readiness.json`.

## Security boundary

This adds review discipline, not cryptographic reviewer identity. Reviewer identity is still a declared string unless a future separately designed signed-identity mechanism is added.

No network request, secret access, quota consumption, or forecasting activation occurs in this phase.
