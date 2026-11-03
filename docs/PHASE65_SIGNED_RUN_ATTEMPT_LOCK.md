# Phase 65 — Signed workflow-attempt authorization lock

Status: **SAFE HOLD / OFFLINE**

Phase 65 adds an independent cryptographic replay control beneath the Phase 62 workflow-level rerun gate.

## Problem

Phase 62 requires `github.run_attempt == 1` at the live-probe job gate. That blocks GitHub job reruns before secret exposure or network execution.

The signed pre-secret execution intent, however, previously bound the workflow run ID but did not explicitly bind the GitHub run-attempt value. The authorization checksum therefore did not independently state that only attempt 1 was valid.

## Signed attempt binding

Execution-intent schema v2 now requires:

`workflow_run_attempt: 1`

The value is included in the canonical body used to calculate `intent_sha256`.

The execution-intent CLI receives the value from:

`GITHUB_RUN_ATTEMPT`

and the contract rejects booleans, zero, values greater than one, strings, or any other non-integer-one value.

Therefore even if the workflow-level job guard were accidentally weakened in a later revision, execution-intent construction itself fails closed on a GitHub rerun before the provider-secret-bearing step is eligible.

## Attestation chain

Execution-intent verification-marker schema v2 also records:

`workflow_run_attempt: 1`

from the verified signed intent.

Artifact ingestion exposes the value from both the execution-intent artifact and its independently verified marker. The preferred GitHub evidence ingester requires both values to equal integer 1 and to match each other.

Because the provider receipt directly binds `execution_intent_sha256`, the receipt transitively binds the first-attempt requirement as well.

## Layered replay defense

After Phase 65, replay rejection exists at multiple independent layers:

1. workflow job gate requires `github.run_attempt == 1`;
2. signed execution-intent schema v2 requires integer attempt 1;
3. signed-intent verification marker schema v2 requires integer attempt 1;
4. GitHub artifact ingestion cross-checks both attempt values;
5. provider receipt checksum-binds the resulting signed execution intent;
6. prepared-probe readiness fails closed if workflow wiring drifts.

## Boundary

This phase does not dispatch a provider workflow, access a provider secret, execute a provider request, promote readiness, activate forecasts, or execute wagers.

The evidence ledger remains schema v5 because the existing durable ledger already retains the exact signed execution-intent checksum and related attestation provenance. The newly checksum-bound attempt is therefore cryptographically covered without changing the ledger record shape.

Global state remains `SAFE_HOLD`.
