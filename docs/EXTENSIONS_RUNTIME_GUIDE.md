# EBT.ai sports extensions — offline implementation and certification gate

**Scope:** EBT.ai Black Diamond sports analytics, not the credit platform. Read the full V7 project master and appended Oct 22 V7.1 before any forecasting, betting decision, market research or audit. The code in this directory is **research-only** and is not a live sports prediction platform.

October 31 correction: read `CALIBRATION_RECOVERY.md`. The numeric qualification
checker never approves a wager. Under-audit records must explicitly identify
`probability_kind: model_forecast`; distinct forecast IDs cannot duplicate the
same event/stat condition. `ebt_quality_cli.py` provides optional chronological
archive diagnostics and conditional research checks, not certified forecasts.

## Installed executable modules

- `extensions/underperformance.py`: complete integer count PMF validation, exact strict-under/push/over probability, P50/P80/P90, central cushion, separate context-normal and predeclared severe-shortfall probability, optional over-friendly recovery state, plus immutable pregame under audit and Brier/log-loss diagnostics. Never seeds projections from sportsbook lines. Does not fit a player distribution.
- `extensions/streak_intelligence.py`: offline final-game CSV import with canonical-ID *format* requirement, operator-approved-use manifest, source URL/time and license checks, DNP exclusion, `GE` inclusive / `GT` strict over / `LT` strict under, pushes and descriptive L5/L10/L20/season. A file saying `contract_reference` or `approved_by` is **not** independent proof of rights. A source URL is **not** verified official identity.
- `extensions/monte_carlo.py`: three purpose-distinct, seed-reproducible >=100k count-PMF simulation runs; hashes input and executing source code, returns win/push/miss counts for baseline/adversarial/scenario. These are **single-outcome diagnostics**, not correlated joint parlay simulations. A supplied PMF is not a calibrated model just because it was sampled 100,000 times.
- `extensions/prop_card.py`: static, HTML-escaped electric black/gold/cyan sports-research card, with labels for matchup, CT event, main/adverse P50, exact strict/inclusive comparator, central/adverse cushion, source freshness category, and modeled probability distinct from calibration. The card **always** displays `FORECAST: HOLD; WAGER: NOT APPROVED` and `MC: NOT RUN` because this renderer does not independently authenticate run provenance. No screenshot counts as evidence.
- `ebt_extensions_cli.py` / `ebt_prop_card_cli.py`: command-line entrypoints with parse/identity/error guards. They make no network calls and do not mutate the original forecasting engine or settle wagers.

## Local usage

```
python -m unittest discover -v
python ebt_extensions_cli.py --help
python ebt_extensions_cli.py under local_data/count_under.json
python ebt_extensions_cli.py under-mc local_data/three_pmf_runs.json
python ebt_extensions_cli.py under-audit local_data/pregame_audit.json
python ebt_extensions_cli.py streak local_data/final_game_logs.csv \
  --approval local_data/operator_rights.json --player-id p1 --stat rebounds \
  --threshold 9.5 --operator lt --as-of-utc 2026-10-29T19:00:00Z
python ebt_prop_card_cli.py local_data/research_card.json --output local_data/card.html
```

Example `count_under.json` (synthetic): `{"pmf":{"8":"0.6","12":"0.4"},"line":"10.5","normal_baseline":"13","severe_fraction":"0.5"}`.

Example `three_pmf_runs.json` (synthetic): `{"pmfs":{"baseline":{"8":"0.6","12":"0.4"},"adversarial":{"8":"0.3","12":"0.7"},"scenario":{"8":"0.5","12":"0.5"}},"line":"10.5","trials":100000,"seeds":{"baseline":101,"adversarial":202,"scenario":303}}`.

Example `research_card.json` (synthetic): `{"subject":"Synthetic Player","opponent":"Synthetic Opponent","event":"synthetic-id","event_ct":"2026-10-29 7 PM","market":"rebounds","comparator":"LT","threshold":"10.5","p50":"8","adverse_p50":"12","model_version":"RESEARCH_ONLY","source_status":"PENDING"}`.

The project should store real source documents, records, manifests and market quotes **privately**, never in this public repository. `local_data/` remains excluded by `.gitignore`. Tests contain only labeled synthetic players/providers.

## Acceptance/activation dependencies (all remain HOLD)

1. Contractually permitted provider endpoints and *independently reviewed* rights, rate, retention, model-use and redistribution constraints; no access bypass or authentication leakage.
2. Official canonical IDs (event/player/team), current role/availability, complete league slate and source-as-of time (TeamRankings primarily team-level).
3. Sport-/market-specific, history- and opponent-based independently fitted model with locked pregame distribution and verified evidence/uncertainty. Count-PMF research does not generalize automatically to yards, shots, time-based events, UFC or golf.
4. Backtesting on pregame frozen forecasts against official final outcomes, calibration cohort gates, bias/leakage checks and independent lower-bound confidence.
5. Three 100k purpose-distinct MC runs on *verified, defensible* model assumptions (the research runner is not certification), plus >=100k dependent joint portfolio simulation if proposing parlays.
6. Exact timestamped operator line/price/settlement terms, no-vig comparison, fair odds, positive EV and final revalidation. A selected alternate line is not necessarily an edge.
7. Human review, monitoring and rollback for a live release. No current source contract, verified pricing or model accuracy was established by these code changes.

**Enforcement:** No research extension writes to `ebt_validation.qualify()` as authoritative verified evidence. No module produces `APPROVED` as a wager status. Existing live/public interfaces remain disabled. No scheduled tasks, external messages, bets or deployment is created here.
