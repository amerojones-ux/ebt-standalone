# OMEGA V8 research integration — NOT PRODUCTION

This branch adds seven research building blocks, not a certified live forecast engine.

1. Beneficiary ranking uses opportunity pool, share, conversion and a fail-closed eligibility gate.
2. Rare events use hurdle survival and a beta-prior zero-event posterior.
3. Combo markets use paired component resampling to preserve observed dependence.
4. Injury, lineup and minutes restrictions generate HOLD reasons.
5. Joint Monte Carlo allocates a shared team opportunity pool across competitors under baseline/adverse scenarios.
6. Temporal backtest computes Brier score and log loss on supplied pre-locked settled outcomes.
7. Audit record hashes chain forecast and settlement payloads.

## Important acceptance limitations

- The simple ranking metric is an expected-count baseline, not a calibrated probability or optimal beneficiary selector.
- The hurdle model needs fitted positive intensity, uncertainty intervals and out-of-sample comparison against negative-binomial and other distributions.
- The paired bootstrap needs more historical observations and explicit minutes/role conditioning.
- Joint MC uses a fixed team opportunity pool and binomial conversion. Production must model team-opportunity variance, correlation, game scripts, usage, player substitutions and reproducible scenario weights.
- The backtest validates ordering and scores but does not fit an isotonic or hierarchical calibrator; add chronological training/validation/test splits with leakage checks.
- Hash chaining alone is not immutability: production needs append-only authenticated storage, concurrency controls and durable settlement identities.
- Official roster/availability source integration, source rights, provider ingestion, calibrated thresholds, regression CI and production wiring are NOT completed.
- No real-game results or >=80%/87% certification claims are made. All records are synthetic and all wagers remain NOT APPROVED.

Run `python -m unittest discover -v`. Do not deploy or merge without review and verified data acceptance.
