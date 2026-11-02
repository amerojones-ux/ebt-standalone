# Phase 45 — Strict GitHub artifact receipt ingestion

Status: **OFFLINE / NO AUTOMATIC PROMOTION**

Phase 42 made sanitized probe receipts downloadable as short-lived GitHub Actions ZIP artifacts. Phase 45 adds a strict ingestion boundary for those downloaded archives.

## ZIP acceptance rules

The ingester accepts only:
- WeatherAPI, The Odds API, or API-Sports;
- a ZIP archive no larger than 1 MiB;
- exactly one ZIP member;
- the exact provider-specific receipt filename;
- no nested path or traversal;
- no directory;
- no encrypted member;
- no symbolic link;
- a receipt payload no larger than 64 KiB;
- valid UTF-8 JSON.

The extracted receipt must still pass the provider-specific checksum/schema verifier and must be a provider-specific PASS receipt eligible for review.

## Correct checksum semantics

A prior implementation used the receipt's internal `receipt_sha256` value as `artifact_sha256`. That was semantically incorrect.

Phase 45 separates them:

- `receipt_sha256` = SHA-256 over the provider receipt's canonical body;
- `artifact_sha256` = SHA-256 over the exact sanitized receipt **file bytes** extracted from the GitHub artifact ZIP.

The review candidate checksum binds both values.

The GitHub ZIP archive is only a transport wrapper. Its container hash is not substituted for the receipt-file hash.

## Output boundary

Successful ingestion returns only a `REVIEW_ONLY` candidate plus sanitized checksum metadata. It explicitly keeps:
- ledger mutation disabled;
- readiness mutation disabled;
- forecast activation disabled.

No provider network, secret, ledger, readiness, or forecast mutation occurs in this phase.
