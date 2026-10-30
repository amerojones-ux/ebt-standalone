# Weather release attestation architecture (design only)

**Status: PROPOSED; NOT IMPLEMENTED; NOT A PRODUCTION AUTHORIZATION MECHANISM.**

The existing `weather_verified_evidence.py` validates only caller-supplied metadata.
It cannot authenticate authorities, verify signatures, establish reviewer identity,
or prove that external evidence exists. Its `APPROVED` integration result is
synthetic/structural and MUST NOT be interpreted as an operational release.

## Trust boundary

1. A protected evidence service—not the forecasting process—collects independently
   reviewed evidence and records immutable references with timestamps.
2. An authorized reviewer signs an exact canonical payload containing: schema version,
   repository, commit SHA, environment, requirement ID, decision, evidence digest,
   reviewer role, issuer identity, issued-at, expires-at, and unique nonce.
3. A verifier loads **pinned public keys** from independently controlled configuration.
   It rejects unknown issuers, unexpected algorithms, expired/not-yet-valid statements,
   mismatched environment/commit, replayed nonces, duplicate evidence, revoked keys,
   and insufficient role separation. Use an established signature library and a
   defined canonicalization format; never invent a custom cryptographic algorithm.
4. A separate authorization service verifies the signatures and evidence provenance
   before it may issue a short-lived release token. This service must also enforce
   the complete platform-wide forecast and wager gates.
5. All approval events and key rotations are append-only and audited. Any missing
   revocation state, time source, evidence store or verification service fails closed.

## Acceptance tests required before implementation is trusted

- Forged issuer, altered payload, incorrect key, wrong algorithm, stale/early
  timestamps, cross-environment replay, cross-commit replay and nonce reuse.
- Conflicting decisions, missing reviewer role, one reviewer approving incompatible
  roles, revoked signer, unavailable evidence service and compromised runner.
- Signature verification against independent known-good test vectors.
- Zero secret or raw evidence leakage into CI logs, artifacts or errors.
- Production release remains blocked until a separate authorized review.

## Current deployment policy

Do not enable live WeatherAPI transport or ingest weather data based on offline
synthetic evidence. Do not merge this design as proof of security readiness.
Forecast: HOLD. Wager: NOT APPROVED.
