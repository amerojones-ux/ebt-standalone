# Phase 42 — Sanitized probe receipts persisted as short-lived workflow artifacts

Status: **PREPARED / NO LIVE REQUEST**

The three prepared one-shot live probes now persist their already-validated sanitized JSON receipt as a GitHub Actions workflow artifact.

Supported probe workflows:
- WeatherAPI
- The Odds API
- API-Sports

## Artifact policy

Each workflow:
- uploads only the single known sanitized receipt JSON file;
- uses `if: always()` so a valid HOLD receipt can still be inspected when the probe step exits nonzero;
- ignores a missing file rather than uploading unrelated content;
- retains the artifact for 7 days;
- uses no wildcard or directory upload;
- does not persist raw provider responses, request URLs, headers, exact quota balances, account/subscription data, or credentials.

The upload action is pinned to the exact official `actions/upload-artifact` v7.0.2 commit:

`cf430e030ddbb5b0abf93d22962f4752f3646cd9`

The receipt itself remains governed by the provider-specific checksum/schema verifier. The GitHub artifact service adds transport/storage provenance but does not turn the receipt checksum into a cryptographic signature.

## Operational benefit

Once a user deliberately runs a manual one-shot probe, connected GitHub tooling can retrieve the workflow artifact directly. That enables exact receipt verification and the existing REVIEW_ONLY evidence pipeline without relying on screenshots, copied console text, or manually reconstructed JSON.

No live provider request, secret read, quota consumption, readiness mutation, or forecast activation occurs in this phase.
