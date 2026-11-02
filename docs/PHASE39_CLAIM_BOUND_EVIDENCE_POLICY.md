# Phase 39 — Claim-bound evidence policy

Status: **SAFE HOLD / OFFLINE**

Phase 37 established that readiness flags require evidence. Phase 39 constrains **which evidence types are allowed for each exact claim** and binds every evidence record to its subject and claim.

## Provider source policy

- `live_auth_verified` → **GitHub Actions receipt only**
- `entitlement_verified` → manual review or validation report
- `identity_verified` → validation report only
- `freshness_verified` → validation report only
- `model_evidence_allowed` → validation report only

A successful authentication receipt therefore cannot be reused as proof of entitlement, player/team identity, feed freshness, or model-evidence suitability.

## Model-gate source policy

All model-level gates require validation reports:

- source provenance
- roster/injury identity
- historical calibration
- joint dependence/correlation validation

## Record binding

Every non-null evidence record must explicitly contain the exact:
- `subject`
- `claim`
- `source_type`
- source reference
- review timestamp
- reviewer

A record placed under another provider or claim fails validation even if all hashes and timestamps are otherwise valid.

GitHub receipt evidence additionally requires its source commit and receipt SHA-256. Validation reports require an artifact SHA-256.

## Time boundary

The normal activation CLI evaluates evidence against current trusted UTC runtime time and rejects future-dated review records. Unit tests use fixed trusted timestamps for deterministic CI.

## Review candidate compatibility

Receipt-to-review candidates now include `subject` equal to the provider and remain strictly `REVIEW_ONLY`. They still cannot mutate readiness, write VERIFIED ledger entries, or activate forecasts.

Expected committed state remains:
- `EVIDENCE_GATE: PASS`
- `GLOBAL_PROVIDER_GATE: SAFE_HOLD`

No network request, secret read, quota consumption, or forecast activation occurs in this phase.
