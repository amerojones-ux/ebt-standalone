# Phase 66 — Signed evidence-review path integrity

Status: **SAFE HOLD / OFFLINE**

Phase 66 hardens the signed provider live-auth evidence-review path to the same replay and source-integrity standard as the live-probe path.

## Review workflow execution controls

The signed evidence-review workflow now requires all of the following before the review job can start:

- `github.run_attempt == 1`
- `github.ref_protected == true`
- `github.ref == 'refs/heads/main'`
- a non-HOLD review decision
- the exact approval phrase when the decision is APPROVE

Review jobs are serialized through:

`ebt-live-auth-evidence-review`

with `cancel-in-progress: false`.

## Immutable review source

The review workflow checks out the immutable dispatch commit:

`ref: ${{ github.sha }}`

and verifies:

- `git rev-parse HEAD == GITHUB_SHA`
- the working tree is clean

before source evidence is reconstructed or a signed review decision is emitted.

## Source probe attempt binding

The review workflow now rejects a source provider run unless GitHub reports:

`run_attempt == 1`

This complements the source probe's own Phase 62/65 protections and prevents a later GitHub rerun state from being accepted as the source execution context.

## Signed review attestation marker v2

The review-decision verification marker is upgraded to schema v2 and checksum-binds:

`review_workflow_run_attempt: 1`

The verifier rejects booleans, zero, strings, or values greater than one.

## Promotion ingestion metadata

The downstream promotion-preview workflow now records the reviewed workflow's GitHub `run_attempt` in the exact artifact metadata passed to strict review-package ingestion.

The review-package ingester independently requires integer attempt 1.

Thus a review artifact cannot be accepted downstream merely because its filenames, hashes and review run ID are valid if GitHub metadata identifies it as a rerun attempt.

## Adversarial coverage

Regression coverage now proves rejection when:

- review artifact metadata reports `run_attempt=2`;
- the signed review attestation marker reports attempt 2 even after recomputing its checksum;
- source review/probe workflow validation omits first-attempt semantics;
- immutable review checkout or protected-ref execution controls drift.

## Boundary

Phase 66 does not dispatch any live-provider probe.

It does not access provider secrets, make provider network requests, write the evidence ledger, update readiness, activate forecasting, or execute wagers.

Global state remains `SAFE_HOLD`.
