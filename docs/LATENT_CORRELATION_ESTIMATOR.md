# Leakage-Safe Latent Correlation Estimator

This layer estimates the dependence matrix consumed by the correlated combo/joint MC engine.

It does not use sportsbook tickets, same-game-parlay prices, payout targets, or post-cutoff outcomes.

## Historical row contract

Every historical observation includes:

- canonical event ID
- variable ID
- numeric settled outcome
- event time
- outcome-available time
- source-record SHA-256

The outcome must become available strictly before the forecast cutoff. Duplicate event-variable rows and inconsistent event times are rejected.

Only events containing every requested variable are used in the correlation fit. Missing-variable events remain visible in:

- historical event count
- complete event count
- complete-case coverage

The system does not silently impute missing outcomes.

## Rank-normal Gaussian-copula estimate

For each variable:

1. sort complete historical values
2. assign midranks for ties
3. convert empirical rank probabilities to standard-normal scores
4. calculate Pearson correlation on the aligned normal scores

This estimates a Gaussian-copula-style latent dependence structure while reducing sensitivity to scale differences and extreme raw count magnitudes.

A zero-variance rank variable is rejected.

## Identity shrinkage

The raw normal-score matrix is shrunk toward identity:

`R_shrunk = (1 - lambda) * R_raw + lambda * I`

The shrinkage amount is predeclared by policy and must be >0. This stabilizes small-sample/off-diagonal estimates and helps ensure a positive-definite matrix suitable for Cholesky simulation.

The resulting matrix is explicitly tested for positive definiteness.

## Pairwise uncertainty

For each off-diagonal raw correlation, the estimator reports an approximate 95% Fisher-z interval.

Policy includes a maximum permitted pairwise CI width. If any pair is too uncertain, the correlation receipt remains HOLD.

These intervals are diagnostics, not calibration guarantees.

## Temporal stability

The latest two equal-size windows are compared:

- previous window
- recent window

Each window independently recomputes the rank-normal correlation matrix. The largest absolute pairwise correlation drift is compared with a predeclared maximum.

A material recent sign/magnitude change forces HOLD even if the full-history matrix looks stable.

## Required policy

The caller predeclares:

- minimum complete events
- recent window size
- shrinkage-to-identity amount
- maximum absolute temporal drift
- maximum pairwise Fisher interval width

No threshold is learned from the current sportsbook market.

## Joint-model bridge

An estimator receipt can feed the Phase-113 joint engine only when:

- status is RESEARCH_INPUT
- shrunk matrix is positive definite
- marginal PMFs exactly match the correlation variable universe
- joint-model lock is not earlier than the correlation forecast cutoff

The estimator's `matrix_sha256` becomes the joint model's source-evidence hash.

## Limitations

This module does not decide which historical cohort is appropriate. The caller must choose a defensible pre-event cohort based on sport, role, lineup, matchup, pace, usage and other model context without looking at the current market price.

It also does not:

- authenticate provider truth
- calibrate correlations to future outcomes
- prove stationarity
- generate sportsbook EV
- approve wagers

Large uncertainty or drift is a HOLD signal, not a reason to force the matrix toward the desired result.

## CLI

`latent_correlation_cli.py` exposes:

- `estimate`
- `build-joint-model`
