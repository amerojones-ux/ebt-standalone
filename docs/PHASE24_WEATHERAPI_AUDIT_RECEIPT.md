# Phase 24 — WeatherAPI integrity-checksum audit receipt

Status: **PREPARED / NO LIVE REQUEST**

A future approved WeatherAPI one-shot probe writes a secret-free JSON receipt to the GitHub Actions step summary. The receipt contains only the provider name, fixed endpoint label, fixed non-personal test location, sanitized result status/category/integer detail, UTC generation time, Git commit, GitHub run ID, and a SHA-256 checksum over the canonical receipt body.

## Integrity boundary
The SHA-256 value is an **integrity checksum, not a cryptographic signature**. It can detect accidental or uncoordinated modification when independently recomputed, but a party that can edit the receipt can also recompute the checksum. Therefore the receipt must not be described as tamper-proof, signed, authenticated, or independently attested.

Schema version 2 includes the explicit field `integrity_model: sha256-checksum-not-signature`. Verification rejects missing/extra fields, unexpected fixed metadata, invalid result categories/details, malformed checksums, and checksum mismatches.

The GitHub workflow independently verifies the generated receipt before publishing it to the Actions step summary. If receipt serialization or verification fails, the workflow exits with an error and reports that the receipt is unavailable/invalid instead of blindly reading a missing file.

The receipt schema rejects unknown result categories and non-integer detail values so raw provider messages, API keys, query strings, headers, and response bodies cannot be serialized through the normal path.

This is limited provenance/integrity evidence for the bounded authentication check only. It is not evidence of forecast accuracy, sports-data coverage, provider-wide entitlement, or production readiness.
