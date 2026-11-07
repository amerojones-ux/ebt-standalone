# Role → Projection → MC → Market Revalidation State Machine

This layer enforces V7/V7.1's material-change rule as an immutable event decision lifecycle.

## Decision evidence binding

Every prior event decision entering this layer must bind:

- decision ID and version
- canonical event ID/key
- model version
- projection lock time
- exact role-evidence SHA-256
- exact market-snapshot SHA-256 and capture time
- decision status

A later official role state is separately fingerprinted. The prior decision is not rewritten.

## Revocation

The prior decision is revoked when:

- the current official role gate is HOLD
- an event-scoped material official role/status/submission change exists
- confirmation is still required

A material change using the same evidence hash or evidence not newer than the prior projection lock is classified as a provenance conflict and remains HOLD.

A nonmaterial source refresh may update evidence availability without automatically revoking the prior projection.

## Replacement order

Once revoked, the required sequence is fixed:

1. confirm current role gate FOUND
2. rebuild the independent projection
3. run MC-1 baseline >=100,000
4. run MC-2 adversarial >=100,000
5. run MC-3 scenario/correlation >=100,000
6. ingest a fresh complete market ladder after the new model lock
7. recalculate price/EV/uncertainty/scenario survival
8. run final V7 revalidation

The old market snapshot is revoked with the old decision.

## Completion receipt

The completion gate requires:

- current role-evidence hash matches the revalidation plan
- replacement projection is bound to that exact role evidence
- projection lock is after current role evidence availability
- three distinct MC receipts each have >=100k trials and provenance hashes
- market capture occurs after the new projection lock
- the oldest quoted price used is not older than the new projection lock
- event ladder completeness is verified
- market price identity is verified

Success means only `READY_FOR_FINAL_V7_QUALIFICATION`. It is **not** APPROVED and cannot bypass calibrated probability, lower-bound, EV, source, scenario, or final live checks.

## NBA bridge

`role_state_from_nba_injury` converts the canonical event-scoped output of the NBA official injury-report layer into a revalidation trigger. Daily/global injury changes from other games cannot contaminate the current event.

No injury status mechanically changes a projection. It only causes the independent opportunity model to rerun.

## CLI

`revalidation_orchestrator_cli.py` exposes:

- `plan`
- `nba-role-state`
- `complete`

The CLI is offline and never makes provider requests.
