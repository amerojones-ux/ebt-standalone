# EBT.ai live provider verification — controlled runbook

## Current status: HOLD

Passing offline CI is **not** proof of live connectivity, source authentication, official reconciliation, or forecast calibration. The existing regression workflow makes no provider calls.

## Authorized live-verification sequence

1. Confirm each provider's subscription, license, approved host, exact endpoint path, auth mechanism, read-only scope, rate quota, and permitted use. Do not guess endpoint paths or secret names.
2. Establish a repository environment with required reviewer approval and no production credentials. Keep secrets in GitHub Actions secrets, never in workflow inputs, command-line arguments, source files, or logs.
3. Build provider-specific endpoint contracts. Reject query-string credentials, redirects, non-HTTPS URLs, unexpected hosts, response oversize, stale timestamps, and schema drift.
4. Use an explicitly dispatched workflow with provider-specific secret mapping and no automatic schedule. Limit to one bounded request per approved endpoint. Do not run if billing or quota impact is unknown.
5. Capture only redacted, minimal response fields and SHA-256 digest. Record provider, endpoint, UTC retrieval time, source publication time, transport/TLS result, schema version, and provenance. A matching digest alone does not authenticate the provider.
6. Independently retrieve the matching event/status from an authoritative official league/team source. Compare identifiers, status, start time, participants, and observation timestamps; record conflicts.
7. Have an authorized reviewer attest to the exact digest, evidence ID, and independent official comparison. Reviewer allowlisting alone is not cryptographic authentication.
8. Only after all live gates pass: run calibrated out-of-sample forecasting and three independent >=100,000-trial simulation paths per authoritative V7 requirements. Independently lock forecasts before comparing sportsbook prices.
9. Require explicit release approval, security review, calibration evidence, rollback rehearsal, and fresh live revalidation before any production forecasting.

## Non-negotiable gates

- No provider endpoint is verified merely because a credential exists.
- No verified source claim from caller-supplied booleans or a self-signed record alone.
- No production activation, wagering approval, or certified EV from offline tests.
- Every blocked, unavailable, conflicting, or stale source remains HOLD.
- No API-key output, endpoint-guessing, subscription upgrades, or chargeable calls without explicit scope approval.

## Outstanding blockers

Provider-specific approved endpoint contracts and secret mapping; authenticated live response evidence; independent official-source captures; verified reviewer provenance; calibrated forecast and scenario survival evidence; controlled release review.
