# Phase 69 — Live-probe runtime evidence repair

Status: **SAFE HOLD / OFFLINE**

Phase 69 fixes two runtime-only defects that static workflow-fragment tests did not catch.

## Defect 1 — execution-intent marker schema mismatch

Execution-intent marker schema v2 requires:

`workflow_run_attempt: 1`

The live workflows generated schema-v2 markers without that field. Downstream strict ingestion would therefore reject the marker after the provider request had already been consumed.

All three provider workflows now include:

`"workflow_run_attempt": intent["workflow_run_attempt"]`

inside the execution-intent marker body.

The generated marker is immediately checked with:

`verify_execution_intent_marker(...)`

before `intent_verified=1` is emitted.

Because the provider secret step already depends on `intent_verified == 1`, an invalid intent marker now blocks the provider request before secret/network access.

## Defect 2 — invalid receipt-marker attempt reference

The receipt attestation marker is schema v4. Its exact-field verifier does not include a workflow-attempt field.

The live workflows incorrectly injected:

`"workflow_run_attempt": intent["workflow_run_attempt"]`

inside the receipt-marker generator. In that Python block, `intent` was not defined, which would raise a runtime error. Even if defined, the extra field would violate the schema-v4 exact-field contract.

The invalid field is removed from all three receipt markers.

Each generated receipt marker is now immediately checked with:

`provider_attestation_verification_marker.verify_marker(...)`

before `attestation_verified=1` is emitted.

## Regression control

The live-workflow security test now scopes assertions to the exact marker-generation steps. It proves:

- the execution-intent marker block contains the required signed attempt;
- the execution-intent marker is self-verified before provider execution;
- the receipt marker block does not reference an undefined `intent`;
- the receipt marker is self-verified before evidence persistence.

The provider readiness registry now requires both runtime marker-verification paths. Drift forces `INVALID_HOLD`.

## Boundary

This repair does not dispatch a live provider workflow.

No provider secret is read and no provider request is performed.

Global state remains `SAFE_HOLD`.
