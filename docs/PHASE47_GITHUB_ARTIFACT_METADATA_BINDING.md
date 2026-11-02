# Phase 47 — GitHub artifact metadata as the preferred provenance source

Status: **OFFLINE / NO PROVIDER EXECUTION**

GitHub's Actions artifact REST response includes artifact identity/status fields and an associated workflow-run object with run ID, branch and head SHA. Phase 47 uses that metadata as the preferred external source for the values required by Phase 46.

## Required metadata checks

For WeatherAPI, The Odds API and API-Sports, the validator requires:

- positive artifact ID;
- artifact size > 0 and <= 1 MiB;
- `expired: false`;
- timezone-aware `created_at` and `expires_at`;
- creation not in the future;
- expiration later than trusted runtime time;
- valid `sha256:<64 hex>` GitHub artifact digest metadata;
- positive workflow run ID;
- positive repository ID;
- matching head-repository ID;
- `head_branch: main`;
- 40-character workflow `head_sha`;
- exact artifact name `<provider-prefix>-<workflow-run-id>`.

The resulting trusted-binding object supplies the run ID and commit to the strict ZIP receipt ingester. A receipt with a different embedded run ID or commit fails closed.

## Digest boundary

The GitHub artifact metadata digest is retained as external provenance metadata. This phase does not claim that its digest encoding necessarily equals a locally computed hash of the downloaded ZIP container.

Separately:
- the receipt's internal `receipt_sha256` verifies its canonical body;
- `artifact_sha256` in the review candidate verifies the exact sanitized receipt file bytes extracted from the ZIP.

These checksums are not conflated.

## Preferred post-run path

GitHub artifact metadata
→ metadata validation
→ trusted run/commit binding
→ strict ZIP ingestion
→ provider receipt verification
→ REVIEW_ONLY candidate
→ reviewer decision
→ dry-run evidence-ledger preview

No ledger/readiness/forecast mutation is permitted by this phase.


## Phase 52 strengthening

Phase 52 additionally requires the downloaded artifact ZIP bytes to match the GitHub artifact record's exact `size_in_bytes` and SHA-256 `digest` before any archive member is parsed. The metadata binding is therefore now a byte-level transport integrity check, not only an identity/shape check.
