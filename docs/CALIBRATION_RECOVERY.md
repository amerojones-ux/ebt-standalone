# Forecast quality recovery — October 31, 2026

Data access, a statistical projection, probability calibration, and wager approval
are different stages. This change repairs offline checks; it does not activate a
live forecasting service or establish an 80% success rate.

## Corrected behavior

- `ebt_validation.qualify` no longer emits VALIDATED or APPROVED from caller flags.
  It reports conditional numeric gate results, explicit unverified research status,
  and `wager: NOT APPROVED`. Existing exact probability/EV checks remain active.
- Under audits reject repeated event/player/stat/line/period conditions even when
  forecast IDs or sportsbooks differ. They require `probability_kind: model_forecast`;
  a missing value is no longer silently treated as a model forecast.
- Count quantiles cannot select zero-mass outcomes at tiny or final quantiles.
- The existing calibration API rejects multiple observations from one event.
- `ebt_forecast_quality` adds an optional strict archive experiment: canonical
  identities, source availability before prediction, generation/lock chronology,
  explicit model probability provenance and final result references. It rejects
  different sports/markets/sides/periods/threshold bands/models/policies in one fit.
- One prospectively specified highest-raw-probability condition per event is selected
  before examining outcomes. Calendar-date blocks in America/Chicago keep an early
  diagnostic/baseline period, calibration fit, and untouched test separate. Earlier
  outcome labels must actually be available before the next block's forecast locks.
  The early block is not a replacement for training the underlying player model.
- A monotone PAV step calibrator is fitted only on the calibration block. Test labels
  do not alter the fit. Scores compare raw, calibrated and early-period constant
  baseline predictions. Reliability is shown by probability band. Raw predictions
  outside observed calibration support are held rather than extrapolated silently.
- Research assessment requires matching cohort/model, no reused evaluation event,
  an earlier finished calibration evaluation, fresh status/market observations,
  unresolved-conflict rejection, opportunity/matchup evidence, and retained receipts
  declaring at least 250k trials for each of the three purpose-distinct MC engines.
  MC3 remains an adverse diagnostic; it is not automatically one-third of the base.

## Provisional sample policy

The default experiment requires at least 100 calibration events and 100 test events;
the relevant 80%+ reliability band needs 100 test events and a one-sided 95% cohort
hit-rate lower bound >=80%. Mean reliability error must be <=5 percentage points;
proper scores must not worsen versus raw forecasts and must improve on the early
constant baseline. These are conservative operational controls, not universal sample
size laws or proof of future accuracy. Dependence across events/teams/seasons remains
a limitation. The cohort bound is **not** an individual forecast probability interval.

`PASSES_LOCAL_RESEARCH_GATE` only means conditional local checks passed. The master
V7/V7.1 Black Diamond requirements (including calibrated >=87% and independently
supported uncertainty lower bound >=80%, cushion and scenario controls) still apply.
Independent archive/source review must bind the exact diagnostic report hash.
Caller assertions, arbitrary reference strings and timestamps cannot authenticate
an archive; this module is not a security boundary against a dishonest caller.

## Usage

```sh
python -m unittest discover -v
python ebt_quality_cli.py calibrate private/pregame_archive.json
python ebt_quality_cli.py assess private/candidate.json --report private/report.json --review private/independent_review.json --asof 2026-11-01T18:00:00Z
```

Read the synthetic schema in `test_forecast_quality.py`. Real archives, API keys,
provider responses, private audit records and reviews must stay outside this public
repository. An empty or unverifiable archive is HOLD. Do not synthesize historical
probabilities from postgame outcomes to fill missing records.

## Modeling and evaluation work still required

Fit player minutes/exposure, opportunities and conversion with roster/role,
opponent, pace, schedule and uncertainty inputs. Use fitted scenario weights and
explicit foul/bench/blowout tails. TeamRankings remains the team-context research
hub; official participation/identity sources take precedence for status. Exact
market snapshots are comparison inputs after independent modeling, not forecast
validation. Separate calibration for materially different cohorts and regimes.

For an API-versus-manual comparison, lock both variants on the SAME events, market
conditions, cutoff times and selection policy. Compare coverage, proper scores and
reliability on a later untouched period. A winning earlier board versus a losing
later board does not identify a causal API effect. Never retune from one night's
losses or force a ten-pick quota. Parlays require separate dependent joint modeling.

References: official scikit-learn probability calibration and temporal validation
documentation: https://scikit-learn.org/stable/modules/calibration.html and
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
