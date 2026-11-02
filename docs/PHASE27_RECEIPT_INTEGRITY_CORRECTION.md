# Phase 27 — Receipt integrity and workflow failure-path correction

Status: **OFFLINE HARDENING / NO LIVE REQUEST**

This phase corrects an evidence-language overstatement and strengthens both prepared live-probe workflows.

## Correction
Earlier WeatherAPI material called the SHA-256 receipt "tamper-evident." A self-contained checksum is not a signature or external attestation: an editor with write access can modify the receipt and recompute the checksum. The correct claim is **integrity checksum**.

Both WeatherAPI and The Odds API receipts now:
- use schema version 2;
- state `integrity_model: sha256-checksum-not-signature`;
- enforce an exact allowlisted schema;
- recompute SHA-256 over the canonical receipt body;
- reject mutations, extra fields, malformed hashes and invalid result fields;
- refuse to write a receipt that fails verification.

Both manual workflows now verify the receipt before placing it in the GitHub Actions step summary. If the probe crashes before serialization or the receipt fails validation, the workflow records a sanitized unavailable/invalid message and exits nonzero.

No signing key was introduced, no false attestation claim is made, and no provider request or credential read occurred during this phase.
