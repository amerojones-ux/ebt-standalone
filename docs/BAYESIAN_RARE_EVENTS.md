# Bayesian Rare-Event Engine

This layer is for sparse markets such as first basket, first touchdown, first goal and exact early-window events. It is intentionally separate from the Black Diamond high-survival board.

## Competing first-event markets

First basket/TD/goal outcomes are mutually exclusive competing events. The engine therefore uses a categorical Dirichlet posterior, not independent binary hit rates.

Every candidate universe must include an explicit residual category such as:

- OTHER
- FIELD_OTHER
- NO_LISTED_CANDIDATE_OR_NO_EVENT

A partial shortlist without a residual category is rejected because renormalizing only the attractive names would inflate their probabilities.

For each category:

`posterior_alpha = prior_alpha + historical_first_event_count`

Posterior mean event probability is the category posterior concentration divided by the total concentration.

The model requires a complete pre-event settled historical sample. Evidence available after the forecast cutoff is rejected.

## Posterior uncertainty

The uncertainty runner performs >=100,000 deterministic-seed Dirichlet posterior draws.

These draws estimate uncertainty in the **latent probability**, not 100,000 game outcomes. Output includes:

- analytic posterior mean
- posterior probability P05/P50/P95
- posterior probability that a candidate is truly the highest-probability category

This does not establish calibration.

## Three rare-event scenarios

Baseline, adversarial and scenario posteriors must use the exact same candidate universe and residual category. Each receives a distinct seed and >=100,000 posterior draws.

For every candidate the engine reports:

- scenario posterior means
- scenario P05/P95
- mean-probability floor
- conservative posterior P05 floor
- posterior P95 ceiling
- rank-1 probability floor

The scenario floor is a robustness diagnostic, not a Black Diamond certification threshold.

## Binary rare events

Some markets are not competing first-event outcomes. Example:

- player scores 3+ points in the first 3 minutes

For one exact predeclared event definition, the engine uses a Beta-Bernoulli posterior:

`posterior_alpha = prior_alpha + successes`

`posterior_beta = prior_beta + failures`

A separate >=100,000 posterior uncertainty runner returns P05/P50/P95 for the latent binary-event probability.

## Market separation

Sportsbook odds are not accepted by either fit schema. Fair decimal odds derived from posterior means are model outputs, not market inputs.

Only after the posterior is locked may the asymmetric-value price layer compare the exact timestamped market quote. Positive value does not imply high hit probability, and rare-event candidates remain outside the Black Diamond survival lane merely because the price is attractive.

## Required downstream controls

Before any real recommendation:

1. verify candidate identity/role/availability
2. verify historical sample provenance and event definition
3. apply sport-specific opportunity/context modeling
4. run actual game-outcome MC-1/MC-2/MC-3 where applicable
5. verify exact market/price after model lock
6. calculate no-vig/fair-price edge under the live rules
7. run adversarial/final V7 revalidation

## Status

Research only:

- no sportsbook input to fitting
- no calibration claim
- no live EV claim
- no wager approval
- no weight update from isolated winning screenshots

## CLI

`bayesian_rare_events_cli.py` exposes:

- fit-competing
- simulate-competing
- three-competing
- fit-binary
- simulate-binary
