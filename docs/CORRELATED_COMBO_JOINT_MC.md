# Correlated Combo Props & Dependency-Preserving Joint Monte Carlo

This layer prevents combo props and parlays from being evaluated by naive independence.

## Inputs

The caller supplies a locked pre-event joint research model:

- complete discrete marginal PMFs for each component variable
- an explicit variable order
- a symmetric positive-definite latent Gaussian-copula correlation matrix
- model lock timestamp
- source-evidence SHA-256

Sportsbook price/odds fields are not accepted by the model schema.

The latent correlation matrix is an external model input. This module does not estimate, calibrate or validate that historical relationship beyond mathematical matrix validity.

## Combo decomposition

A combo leg is expressed as positive component terms, for example:

- Points + Rebounds + Assists
- Points + Rebounds
- Rushing + Receiving yards

The decomposition report shows:

- each marginal mean
- each component's mean contribution
- pairwise latent correlations
- maximum absolute latent correlation
- whether a dependence model is required

A combo with material dependence should not be treated as the convolution of independent components.

## Gaussian-copula discrete simulation

For every trial:

1. draw correlated latent normals through Cholesky decomposition
2. transform each latent value through the normal CDF
3. map the uniform value into the locked discrete marginal PMF
4. calculate each combo/leg expression from the same joint trial
5. settle HIT/PUSH/MISS under exact comparator semantics

The method preserves the supplied marginals while imposing the supplied latent dependence structure. With discrete margins, realized Pearson correlation need not equal the latent correlation input.

## Combo dependence diagnostic

`compare_combo_correlated_vs_independent` runs:

- a correlated combo simulation
- an identity-correlation diagnostic using the same marginal PMFs

The delta in simulated hit rates shows how much the dependence assumption changes the combo result. The independent run is a diagnostic, not a preferred model.

## Joint parlay probability

`simulate_joint_model` calculates:

`joint_probability = all_legs_hit / total_trials`

Individual leg probabilities are never multiplied to produce the joint result.

Outputs include:

- each leg hit/push/miss rate
- direct all-legs-hit joint probability
- push-without-miss rate
- dominant failure leg
- top shared failure clusters
- exactly-one-miss rate
- mean/max absolute latent correlation
- model/input/code provenance hashes

## MC-1 / MC-2 / MC-3

`run_three_scenario_joint_mc` requires:

- baseline model
- adversarial model
- scenario/correlation model
- >=100,000 trials each
- three distinct seeds
- identical leg and variable universes

It records:

- joint probability for each scenario
- joint scenario floor
- per-leg hit-probability floors
- dominant failure leg by scenario
- exact leg-definition hash
- scenario receipt hash

## Separate final joint parlay simulation

V7 requires a separate final joint simulation after MC-1/2/3.

`run_final_joint_parlay_mc` requires:

- a seed distinct from all three scenario seeds
- the same exact variable universe
- the same exact leg definitions
- an untampered three-scenario receipt

The final output still remains HOLD / NOT APPROVED until all source, calibration, price/EV and final revalidation gates pass.

## Limitations

This engine does not:

- estimate correlation from raw history
- prove the supplied correlation is stable
- authenticate source data
- calibrate simulated probabilities
- ingest sportsbook prices
- approve wagers

Correlation matrices must be derived and validated from pre-event historical/context data separately. Large unstable correlations should trigger adversarial review rather than automatic confidence.

## CLI

`correlated_joint_mc_cli.py` exposes:

- decompose
- simulate
- compare-combo
- three-scenario
- final-joint
