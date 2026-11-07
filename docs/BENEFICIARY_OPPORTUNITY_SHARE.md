# Beneficiary Competition & Opportunity-Share Model

This research layer answers a narrow question after a verified role change:

> If a player loses confirmed opportunity, how much of that finite opportunity pool can each remaining player defensibly absorb?

It does **not** answer whether a sportsbook prop is good, and it accepts no sportsbook price or line as an input.

## Conservation model

For one metric at a time (for example minutes, touches, field-goal attempts, potential assists, rebound chances or shots):

1. the caller supplies a complete pre-event roster budget
2. baseline player units must exactly reconcile to the team budget
3. scenario-OUT players create displaced units
4. a predeclared redistribution fraction determines how much of that pool remains available to identified beneficiaries
5. active players compete for the same finite pool
6. hard per-player capacity caps prevent impossible allocations
7. opportunity that cannot be defensibly assigned remains explicit team contraction/unassigned units

The model never forces 100% of removed opportunity onto the most obvious replacement.

## Bayesian competition evidence

Each active player has:

- `prior_alpha`: pre-event prior concentration for receiving displaced opportunity
- `context_units`: verified pre-event comparable-context allocation evidence

The posterior concentration is:

`posterior_alpha = prior_alpha + context_units`

Posterior competition share is each player's concentration divided by the active-player concentration total. This is a Dirichlet-style allocation posterior, not a calibrated prop-hit probability.

All evidence has an availability timestamp. Any evidence after the forecast cutoff is rejected.

## Capacity-aware water filling

The target displaced pool is allocated in proportion to posterior concentration. If a player's proposed increment exceeds their remaining capacity, that player is capped and the residual pool is reallocated among the remaining eligible players.

If total capacity is insufficient, the residual stays unassigned. That residual is visible in both:

- `capacity_residual_from_target`
- `team_contraction_or_unassigned_units`

## Beneficiary competition diagnostics

Outputs include:

- displaced units
- target redistribution
- actual allocated units
- player posterior competition share
- allocated increment
- final expected units
- opportunity multiplier
- increment share
- allocation HHI
- largest increment share
- beneficiary ranking

HHI describes how concentrated the displaced opportunity is among beneficiaries. It is a structural diagnostic, not a hit probability.

## Scenario comparison

`run_reallocation_scenarios` can vary:

- redistribution fraction
- explicit ACTIVE/OUT assumptions

It returns each player's:

- increment floor/ceiling
- final-unit floor/ceiling
- whether the player gains opportunity in every supplied scenario

Questionable/Probable/Doubtful statuses are not silently converted into ACTIVE/OUT by this module. Availability scenarios must be explicit and originate from the role-state layer.

## Market separation

The exact roster schema contains no sportsbook fields. Extra fields such as a sportsbook line are rejected. Market comparison happens only after the independent opportunity model and downstream projection are locked.

## Status

This module is research-only:

- no calibrated probability
- no wager approval
- no automatic projection certification
- no postgame evidence
- no forced beneficiary

The resulting opportunity distributions must still feed the sport/market-specific projection, MC-1/2/3, calibration, market comparison and final V7/V7.1 gates.

## CLI

`opportunity_reallocation_cli.py` exposes:

- `allocate`
- `scenarios`

It makes no network calls.
