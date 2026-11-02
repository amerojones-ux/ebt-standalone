# Phase 52 — Bind downloaded artifact bytes to GitHub metadata digest

Status: **OFFLINE / NO LIVE PROVIDER EXECUTION**

GitHub Actions exposes a SHA-256 digest and size for each uploaded artifact. Phase 52 requires the bytes downloaded through the GitHub Actions artifact API to match that metadata before any ZIP content is parsed.

## Transport-integrity gate

For both:
- the sanitized provider receipt artifact;
- the attestation-verification marker artifact;

the preferred GitHub ingestion path now checks:

1. downloaded object is bytes;
2. downloaded byte length exactly equals GitHub `size_in_bytes`;
3. SHA-256 of the downloaded ZIP bytes exactly equals the GitHub artifact `digest`;
4. only after those checks does strict ZIP/member validation run.

A mismatch fails closed before JSON parsing, receipt validation, marker validation, reviewer-candidate construction, or evidence processing.

## Why this matters

The existing layers already validate:
- artifact ID/name/run/branch/commit metadata;
- strict ZIP shape;
- exact provider receipt filename;
- receipt checksum/schema;
- signed attestation verification;
- verification-marker checksum/schema;
- reviewer and ledger provenance.

Phase 52 adds the missing transport binding between the GitHub artifact record and the actual bytes delivered by the download endpoint.

The preferred path now binds:

GitHub artifact metadata
→ exact downloaded ZIP size + SHA-256
→ strict ZIP structure
→ exact sanitized file bytes
→ provider/attestation verification
→ REVIEW_ONLY candidate.

## Scope

This does not make a provider request and does not touch provider credentials.

The committed state remains:
- provider reconciliation: SAFE_HOLD
- global provider/model gate: SAFE_HOLD
- live probes: PREPARED_DEFAULT_DENY
- forecasting: disabled
