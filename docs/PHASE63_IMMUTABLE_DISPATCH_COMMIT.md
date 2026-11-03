# Phase 63 — Immutable dispatch-commit checkout

Status: **SAFE HOLD / OFFLINE**

Phase 63 closes a source-provenance time-of-check/time-of-use boundary in the prepared live-provider workflows.

## Problem

A manual GitHub `workflow_dispatch` event records an immutable `GITHUB_SHA`, and the signed execution intent, receipt provenance and attestation verification all bind that commit.

The live-probe workflows previously checked out mutable `main` by name. If `main` advanced after dispatch but before checkout, the Python code actually executed could differ from the commit named by `GITHUB_SHA` and preserved in the signed evidence chain.

That does not expose a secret by itself, but it breaks exact source-to-execution provenance.

## Immutable checkout

WeatherAPI, The Odds API and API-Sports now check out:

`ref: ${{ github.sha }}`

instead of `ref: main`.

Immediately after checkout, each workflow verifies:

`git rev-parse HEAD == GITHUB_SHA`

and requires a clean working tree before toolchain setup, execution-intent construction or any secret-bearing probe step can occur.

A failed source check stops the job.

## Readiness enforcement

The offline prepared-probe registry now requires:

- checkout of the immutable dispatch SHA;
- explicit HEAD equality with `GITHUB_SHA`;
- a clean working tree;
- absence of mutable `ref: main` checkout.

Drift changes the probe from `PREPARED_DEFAULT_DENY` to `INVALID_HOLD`.

Regression tests specifically reject a mutable-main checkout and removal of the HEAD verification.

## Relationship to Phase 62

Phase 62 prevents reuse of one manual dispatch through GitHub job reruns and serializes all live-provider probes.

Phase 63 ensures that the code executed by the permitted first attempt is the exact commit recorded by the signed execution-intent and receipt evidence chain.

Together the control path is:

manual exact authorization -> first workflow attempt only -> globally serialized probe lane -> immutable dispatch commit -> signed pre-secret execution intent -> exact one-request plan -> provider request -> intent-bound receipt -> signed receipt evidence.

## Boundary

No live-provider workflow is dispatched by this phase.

No provider secret is read, no provider request is issued, no evidence/readiness record is promoted, forecasting remains disabled and no wager action exists.

Global state remains `SAFE_HOLD`.
