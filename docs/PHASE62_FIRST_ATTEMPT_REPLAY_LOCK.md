# Phase 62 — First-attempt replay lock and global live-probe serialization

Status: **SAFE HOLD / OFFLINE**

Phase 62 closes a workflow-level replay boundary discovered after Phase 61.

The signed execution intent and receipt chain already limited each probe implementation to one HTTP request, but the GitHub Actions live-probe jobs did not independently reject a GitHub job rerun. A workflow rerun can preserve the original manual `workflow_dispatch` inputs while incrementing `github.run_attempt`. Without a first-attempt guard, that creates another opportunity to execute the provider-request step under the original dispatch authorization.

## First-attempt execution lock

All three prepared live-provider workflows now require:

`github.run_attempt == 1`

at the job gate, in addition to the existing exact approval phrases and `refs/heads/main` restriction.

A GitHub rerun therefore cannot enter the live-probe job. A new request requires a new manual workflow dispatch with the exact provider-specific authorization inputs.

The offline readiness registry treats the first-attempt guard as mandatory. Removing or weakening it changes the probe from `PREPARED_DEFAULT_DENY` to `INVALID_HOLD`.

## Cross-provider serialization

All three live-probe workflows share one concurrency group:

`ebt-live-provider-probes`

with:

`cancel-in-progress: false`

This prevents WeatherAPI, The Odds API, and API-Sports live-auth probes from executing concurrently. Separately authorized dispatches are serialized rather than cancelled or overlapped.

The readiness registry requires the shared group and rejects `cancel-in-progress: true`.

## Adversarial tests

Phase 62 adds regression coverage proving that readiness becomes `INVALID_HOLD` when:

- the first-attempt guard is weakened or removed;
- the shared concurrency group is changed;
- in-progress live probes are configured to be cancelled.

The live-probe workflow invariant suite also requires the exact first-attempt and serialization controls for all three providers.

## Boundary

This phase does not dispatch any live-provider workflow.

It does not access provider secrets, perform provider network requests, mutate the provider evidence ledger, change provider readiness to approved, enable forecasting, or execute wagers.

The platform remains:

- provider/model gate: `SAFE_HOLD`
- prepared probes: `PREPARED_DEFAULT_DENY` when all static invariants pass
- forecast activation: disabled
- wager execution: none

Phase 62 is an execution-control hardening change only.
