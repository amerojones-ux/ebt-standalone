# Phase 61 — Directly bind post-request receipts to signed execution intent

Status: **SAFE HOLD / OFFLINE**

Phase 60 makes the signed one-shot execution authorization durable in ledger v5. Phase 61 strengthens the request/receipt relationship itself: every provider receipt now checksum-binds the exact signed execution intent that authorized the request.

## Receipt schema changes

The sanitized provider receipt body now requires:

`execution_intent_sha256`

Schema versions are:

- WeatherAPI receipt: v3
- The Odds API receipt: v3
- API-Sports receipt: v2

Receipt construction rejects a missing, non-hex or non-64-character execution-intent checksum.

Because the field is included in the canonical receipt body, the existing `receipt_sha256` also covers the authorization checksum.

## Workflow binding

After the pre-secret intent JSON is checksum-verified, the provider workflow emits only the sanitized:

`intent_sha256`

as a step output.

The provider-secret-bearing probe step then receives:

`--execution-intent-sha256 "${{ steps.intent.outputs.intent_sha256 }}"`

and writes that value into the sanitized receipt.

No provider secret is exposed by this output.

## Candidate binding

The pending receipt candidate now checksum-binds the receipt's `execution_intent_sha256` even before the execution-intent attestation is accepted.

The final attestation binder refuses to promote the candidate if the independently verified execution-intent checksum differs from the receipt-bound checksum.

This makes the invariant intrinsic to the candidate layer rather than relying only on the higher-level GitHub artifact ingester.

## Full GitHub ingestion

The Phase-59 source-run ingester independently compares:

receipt.execution_intent_sha256
=
verified execution-intent artifact.intent_sha256

A receipt can therefore be:
- structurally valid;
- internally checksum-valid;
- correctly GitHub-attested;

and still be rejected if it names the wrong authorizing intent.

## Prepared-probe registry

`PREPARED_DEFAULT_DENY` now additionally requires:

- the verified intent step to export the intent checksum;
- the live probe command to pass that exact step output into receipt creation.

Removing or substituting the direct binding changes the prepared probe to `INVALID_HOLD`.

## Boundary

This phase creates no live provider traffic. It changes only offline receipt schemas, workflow wiring, verification logic and tests. Provider secrets remain inaccessible until the signed pre-secret intent gate succeeds, and forecast/readiness state remains unchanged.
