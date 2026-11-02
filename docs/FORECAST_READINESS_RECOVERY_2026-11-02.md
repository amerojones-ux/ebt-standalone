# Forecast readiness and parlay validation gates — 2026-11-02

Status: **RESEARCH HOLD**. This document does not certify models, authorize wagers, or deploy code.

## Evidence confirmed from repository
- `config/module_readiness_2026_10_30.json` marks official slate/role, licensed stats, operator quotes, calibrated models and production API as false.
- `extensions/monte_carlo.py` performs independent count-PMF diagnostics, **not** dependent joint parlay simulations.
- Historical overlay lacks independently certified pregame forecast records; synthetic tests cannot certify real-world accuracy.
- Research documentation reports source HTTP 403; never bypass access controls.

## P0: provider acceptance
For each authorized provider, document contract/rights, approved endpoint, coverage, UTC capture and effective timestamps, authentication success without logging credentials, status, schema version, rate limits, completeness, and canonical IDs. Failed or stale fields => HOLD. Never infer a key is valid from its presence in Secrets.

## P1: immutable pregame ledger
Capture forecast_id, event_id, player/team canonical IDs, competition, market, comparator, line, forecast distribution, model version/hash, source capture IDs/hashes, issued_at, event_start, injury/role state, quote timestamp, and all postgame outcomes including void/push. Reject postgame data leakage, missing identity or timestamp, and retroactive edits. Store sensitive records privately.

## P2: calibrated models
Fit sport/market-specific models using rolling-origin training and chronologically later held-out events; cluster uncertainty by game. Evaluate Brier, log loss, reliability buckets, baselines, confidence intervals, subgroup drift, and selection bias. Do not assert 80%+ without out-of-sample evidence and a defensible lower bound.

## P3: joint parlay validation
Model shared game scripts, minutes, pace, opportunities and correlated outcomes using a jointly simulated distribution. Validate marginal and joint calibration out of sample. Report joint win/push/void settlement, fair odds, offered price, expected value and uncertainty. Do not multiply independent marginals for SGPs. Require verified current quotes and terms; otherwise HOLD.

## P4: prospective shadow acceptance
Lock policies before prospective testing; run forecast-only without wagers. Audit every candidate and every miss, not just published winners. Release requires signed human acceptance, verified data rights, reproducible model artifacts, successful live-provider checks, calibrated holdouts, monitoring and rollback.

## Priority defect register
| ID | Severity | Gap | Acceptance evidence |
|---|---|---|---|
| BD-001 | Critical | Live provider acceptance unverified | Dated redacted provider receipts and contract review |
| BD-002 | Critical | No certified historical pregame ledger | Immutable audited records and official settlements |
| BD-003 | Critical | Real model calibration unverified | Rolling held-out reliability report |
| BD-004 | Critical | No dependent joint SGP simulation | Tested joint simulator and held-out joint calibration |
| BD-005 | High | Official event/player/role mapping incomplete | Reconciled IDs, slate and timestamped injuries |
| BD-006 | High | Prop-card provenance not authenticated | Signed model/run evidence with HOLD fallback |

No secrets, production changes, deployments or betting actions are authorized by this document.
