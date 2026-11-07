# V7 Learning-Change Governance

This layer enforces the authoritative V7 safeguards that must be satisfied before any proposed model-weight or threshold change may enter human review.

It never applies a weight, changes a threshold, promotes a model, or changes a live forecast.

## Exact V7 evidence gates

A proposed learning change requires all of the following:

- at least **30 settled observations for the market**
- at least **50 settled observations for the model**
- at least **two non-overlapping degraded windows**
- each degraded window must show either:
  - Brier worsening >= **0.02**, or
  - current calibration gap >= **0.05**
- completed root-cause review
- completed held-out backtest
- a new proposed model version
- an explicit rollback version and rollback path

The market/model settled counts are bound to immutable sample-ledger SHA-256 values.

## Degraded windows

Each window records:

- window ID
- start/end
- settled count
- reference Brier
- current Brier
- current calibration gap
- evidence SHA-256

The window must finish strictly before the learning-review cutoff.

Windows may touch at a boundary but may not overlap.

A window qualifies when:

`Brier_current - Brier_reference >= 0.02`

**OR**

`calibration_gap_current >= 0.05`

A request with fewer than two qualifying windows remains HOLD.

## Root-cause firewall

A completed root-cause review records:

- completion time
- finding
- pregame identifiability classification
- whether the conclusion is based only on isolated outcomes
- immutable evidence items

The V7 identifiability classes are:

- PRE_GAME_IDENTIFIABLE
- PARTIALLY_IDENTIFIABLE
- POSTGAME_ONLY

POSTGAME_ONLY findings remain research observations and do not qualify as production-learning evidence in this review gate.

Screenshots, tickets, and isolated outcomes may be supplemental audit evidence, but they cannot be the only root-cause evidence and cannot authorize a model change.

## Held-out backtest

The backtest must bind:

- current/baseline version
- proposed/candidate version
- held-out event count
- baseline and candidate Brier
- baseline and candidate calibration gap
- evidence SHA-256

The gate reports candidate-minus-baseline deltas.

V7 requires a backtest but does **not** specify a universal numerical improvement threshold for promotion. This module therefore does not invent one. A completed backtest can make the request eligible for human review even when its diagnostics are unfavorable; the request is still not promoted or applied.

A separate acceptance/promotion decision must judge whether the candidate is actually superior and safe.

## Versioning and rollback

The proposed version must differ from the current version.

The rollback version must equal the current version, and a nonempty rollback path is mandatory.

The backtest baseline/candidate versions must match the current/proposed versions exactly.

## Immutable review receipt

The review output is SHA-256 fingerprinted across:

- sample counts and sample hashes
- degraded-window evidence
- root-cause evidence
- backtest
- versioning
- proposed change
- review eligibility and reasons

Receipt verification rejects tampering.

## Non-negotiable no-apply state

Every output includes:

- `weight_change_applied = false`
- `threshold_change_applied = false`
- `model_promotion_applied = false`
- `requires_human_acceptance = true`
- `forecast_status = HOLD`
- `wager_status = NOT APPROVED`

The strongest possible result is:

`LEARNING_CHANGE_REVIEW_ELIGIBLE`

That means only that the V7 evidence package is sufficiently complete to be reviewed. It does not authorize deployment.

## CLI

`learning_change_governance_cli.py` exposes:

- `assess`
- `verify`
