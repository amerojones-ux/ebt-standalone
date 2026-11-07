# Immutable Daily Audit Ledger

This layer connects the Black Diamond forecasting, market, simulation, settlement, reverse-engine, calibration and learning components to one append-only daily evidence ledger.

It builds on the repository's existing SHA-256 chain primitive and adds legal V7/V7.1 lifecycle transitions.

## Core principle

**Postgame information may append to the ledger but may never rewrite the pregame record.**

Every record stores:

- schema version
- America/Chicago audit date
- record type
- subject
- canonical event identity when applicable
- event start
- effective time
- recorded time
- optional superseded-record reference
- artifact references
- type-specific data

Every chain entry also stores:

- record ID
- previous record SHA-256
- its own SHA-256

A stale writer cannot append when its expected last hash does not match the current ledger tail.

## Pregame record types

The following must be effective **and recorded before event start**:

- `PREGAME_SOURCE_EVIDENCE`
- `PREGAME_MODEL_ARTIFACT`
- `PREGAME_FORECAST_LOCK`
- `PREGAME_DECISION`
- `ROLE_REVALIDATION`
- `MARKET_SNAPSHOT`
- `MC_RECEIPT`
- `SHADOW_CANDIDATE`
- `REJECTED_CANDIDATE`

Examples of model artifacts that can be bound here include:

- opportunity discovery
- beneficiary reallocation
- Bayesian rare-event posterior
- latent-correlation estimate
- combo decomposition
- calibration candidate diagnostics

The exact receipt can be hashed with `artifact_ref_from_receipt`; tampering changes the artifact hash.

## Decision versioning

The first `PREGAME_DECISION` must be version 1.

A later decision version must:

- append a new record
- supersede the latest prior decision record
- keep the same decision ID and event
- increment the decision version by exactly one

A `ROLE_REVALIDATION` record must reference an existing prior decision and declare the exact next replacement version.

The prior record is never mutated.

## Market and simulation controls

A market snapshot cannot be effective before its model lock.

Every `MC_RECEIPT` requires:

- recognized MC purpose
- >=100,000 trials
- input SHA-256
- code SHA-256

The ledger can therefore preserve MC-1, MC-2, MC-3 and final joint-parlay receipts separately.

## Settlement

A settlement:

- occurs after event start
- references an existing pregame decision
- requires an official verified result
- carries an official result-source SHA-256

The first settlement is version 1.

An official stat correction must append a new settlement version that:

- supersedes the latest settlement
- increments by one
- includes a revision reason

No prior settlement is rewritten.

## Postgame reverse audit

A `POSTGAME_REVERSE_AUDIT` must reference:

- the original decision
- a concrete settlement record

It records:

- PRE_GAME_IDENTIFIABLE / PARTIALLY_IDENTIFIABLE / POSTGAME_ONLY
- STRUCTURAL_CANDIDATE / MIXED_OR_UNCERTAIN / RANDOM_OR_UNRESOLVED
- observed mechanism
- failure mechanism

The record itself must always carry:

`pregame_evidence_eligible = false`

Even when the mechanism is classified PRE_GAME_IDENTIFIABLE, the postgame record cannot be backfilled into the original pregame evidence ledger.

## Calibration and learning review records

Global review records have no event identity.

`CALIBRATION_REVIEW` is forbidden from claiming:

- calibration_verified = true
- model_promotion_applied = true

`LEARNING_REVIEW` is forbidden from claiming:

- weight_change_applied = true
- threshold_change_applied = true
- model_promotion_applied = true

This keeps review evidence separate from an actual controlled promotion process.

## Daily summary

The summary validates the entire chain first and then reports:

- record count
- event count
- record counts by type
- unique decision count
- settled decision count
- unsettled decision IDs
- current chain tail

It never mutates the ledger or model.

## CLI

`immutable_daily_audit_cli.py` exposes:

- `validate-payload`
- `validate-ledger`
- `summary`
- `append`
- `artifact-ref`

All operations are offline. The append command uses a caller-supplied expected tail hash to prevent stale concurrent writes.
