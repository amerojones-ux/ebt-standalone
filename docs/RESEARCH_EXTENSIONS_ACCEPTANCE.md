# Streak and underperformance extensions: import, gates and sign-off

**Current status:** CODE IN SEPARATE OFFLINE ARCHIVES — NOT LIVE-INTEGRATED. Acceptance requires both the complete V7/V7.1 specification and tested production source adapters.

## A. Underperformance engine research v1 (2026-10-29)
Archive: `EBT_Black_Diamond_Underperformance_Engine_V1.zip`. Includes `under_engine.py`, `backtest.py`, documentation, source ledger and 16 synthetic tests, locally rerun and passed during reconciliation. The kernel accepts a COMPLETE PMF of nonnegative count outcomes; unsupported yards/ratio/period markets require sport-specific adapters. It does not fit distributions.

For each independent pregame-locked distribution calculate:
- **Market under:** `P(Y < L)` with exact settlement direction, whole-line push mass and known operator rules.
- **Below role-adjusted normal:** `P(Y < B)`, where `B` is a context-matched independently estimated baseline.
- **Material underperformance:** `P(Y <= (1-d)B)`; fix `d` before looking at results.
- Median and percentile forecast, central/adverse under cushion, role/exposure risk, stronger *over-friendly* recovery scenarios, plus strongest evidence *against* the under.
- Separately model minutes, chances/volume, conversion, role competition, pace/game script, foul/injury states. Do not count the same rotation decline three times.
- Historical tests must use an immutable pregame lock, full comparable denominator (including losing unders), official final result, and no hindsight. Rebound drop cases do not establish pregame detectability.

No distribution fitted, historical full-sample backtest, player-level calibration, live quote/EV, production jobs or MC runs were certified by this archive. Keep **HOLD**.

## B. Rights-safe streak intelligence v3 (2026-10-29)
Archive: `EBT_V7_1_Rights_Safe_Importer_v3_2026-10-29.zip`; includes `engine.py`, `ingest.py`, `ingest_v3.py`, 27 observed passing synthetic tests.
- Count consecutive exact-threshold results and L5/L10/L20/season descriptive rates; DNP excluded, PUSH counted separately, unique final official IDs required, latest-first.
- `ingest_v3` requires separate operator-reviewed approval manifest explicitly permitting **sports_betting_analytics**, validity times and source. Manifest assertions are not independent proof of rights.
- Date, capture time, event ID, license scope, malformed values, mixed providers and credential-bearing URLs must fail closed. Direct NBA.com/NBA Stats bulk data requires permission.
- Streaks are descriptive, not calibrated `P(next event hit)`. They must never seed a projection or authorize a wager.
- Do not ship `verified_log_seed.csv` as a certified log: it lacks a resolved official unique game ID.

## C. Promotion checklist
- [ ] Reviewed provider contract and redistribution/model-use terms with independent proof.
- [ ] Complete canonical game/player/team ID mapping and current official role/injury source.
- [ ] Verifiable raw capture receipts, immutable source as-of timestamps, parser/schema tests and no violations of terms.
- [ ] Separate sport/market opportunity and distribution fitting with leakage-safe walk-forward evaluation.
- [ ] Externally certified final outcome archive and enough observations for V7 learning/calibration gates.
- [ ] Actual three independent >=100,000-trial MC runs per serious prop, persisted seeds, input/code hashes, hit counts and scenario/adversarial results.
- [ ] Exact operator book/market/line/odds/timestamp and settlement terms; no-vig, target ceiling and positive EV checked *after* independent model lock.
- [ ] Qualified single registry, <=1 PRIMARY/event, at most one SAFER ALT and REPLACEMENT, joint simulations for any parlay.
- [ ] Adversarial review, security/code review, release approval, rollback protocol and verified live monitoring.

No check above is implicitly completed by the separate 16/27 tests.
