# Collection, extraction and calibration research pipeline

## Boundaries

These components implement previously missing code paths. They do not establish that live providers are accessible, certify source truth or approve model probabilities. Public sources can reject requests; HTTP 403, robots denial, redirects requiring review, unexpected content and parse failures remain HOLD. No alternate fingerprint, authenticated cookie, hidden endpoint, proxy rotation or protection bypass is used. Raw captures stay in ignored `local_data/`.

## Collect and preserve bytes

```sh
python3 ebt_cli.py collect \
  'https://www.teamrankings.com/nba/stat/opponent-three-pointers-attempted-per-game?date=2026-10-28' \
  --destination local_data/raw --timeout 10
```

Supported endpoints are HTTPS dated NBA stat pages on www.teamrankings.com and the exact NBA CDN `todaysScoreboard_00.json` URL defined in `ebt_collect.py`. The collector checks robots before content, rejects redirects, limits duration/bytes, identifies itself, preserves response bytes by content hash and emits a separate receipt. An absent robots file with HTTP 404 is treated as no declared restrictions; other HTTP errors stop collection. A `COLLECTED` receipt records retrieval time only, never an invented publication/effective time. Source-effective dates must still be established before constructing live evidence records. HTTP headers and a declared source URL alone do not prove origin authenticity.

## Reproduce extraction

```sh
python3 ebt_cli.py extract local_data/raw/RECEIPT.json \
  --raw-root local_data/raw --parameters local_data/parameters.json
```

TeamRankings parameters: `expected_heading`, exact `column`, and `expected_rows`. These must be reviewed from the actual page. No latest-year/first-number guess is made. The parser checks a unique Rank/Team table, heading, column identity, row count, rank/team duplicates, links and numeric values. Missing `--` is not zero. Percent text stays in percentage-point units. Table changes or ties/ambiguous layouts requiring a changed adapter fail closed. Outputs contain source team names and links; canonical team-ID mapping remains separately unverified.

NBA scoreboard parameters: `expected_date` in ISO date form. The parser verifies league/date, ten-digit game IDs (keeping leading zeros), team IDs, aware UTC start times and known status codes. Feed row count does not establish independently corroborated slate completeness, tomorrow coverage, active rosters, injuries or workload. Other NBA APIs and injury PDF extraction remain unsupported by this initial adapter set.

To check a saved extraction claim, add `--verify-claim local_data/claim.json`. The code rehashes and reparses the capture using the claim's recorded parameters and compares every output. Editing a claimed value fails verification. This verifies reproducibility of extraction, not source truth or parameter appropriateness. It does not automatically set any forecast qualification flags.

## Temporal calibration candidate

```sh
python3 ebt_cli.py calibrate local_data/training.json \
  --validation local_data/validation.json --settings local_data/calibration_settings.json
```

Settings contain `scope`, `fit_at`, `assessed_at` and `policy`. Scope contains nonempty `competition`, `market`, `threshold_type` and `model_version`; all rows must match. Copy the reviewed policy from `config/calibration_research_policy.json` into settings. Its 50 training/50 validation rows and 30 events per split are conservative engineering research minima, not evidence of adequate accuracy or a universal statistical sample requirement. Lock/version policy before examining held-out outcomes; never lower it to rescue a candidate.

Rows require `forecast_id`, `event_id`, `certified: true`, exact raw probability `p`, HIT/MISS `result`, `training_end`, `issued_at`, `event_start`, `outcome_available_at` and the scope fields. Certification flags must be externally supported by immutable pregame ledgers and verified final outcomes. Push/void/pending outcomes require separate accounting and cannot enter this binary fit. Missing timestamps must not be reconstructed from postgame information.

Training outcomes must be available by `fit_at`. Validation forecasts must be issued strictly after `fit_at`; all outcomes must be available by `assessed_at`. Duplicate forecast IDs, overlapping events across splits, scope changes and time leakage are rejected. Distinct event minima prevent many correlated same-game forecasts from pretending to be many independent events; they do not fully quantify residual dependence.

The pool-adjacent-violators algorithm fits a monotone step map on training rows only. Held-out outcomes do not change the fitted map or rescue failures. Reports retain input hash, block counts, raw/calibrated Brier and log loss, reliability buckets and explicit infinite-loss flags. Endpoint probabilities can be 0 or 1; poor held-out behavior remains visible. Sparse reliability buckets, confidence bounds, selection bias, clustering, regime drift, prospective shadow forecasts and release criteria need separate review. This is one held-out temporal split, not a complete automated rolling backtest.

`calibration_certified` and `forecast_approved` always remain false. The assessment may return `RESEARCH_FIT_EVALUATED`, never validated Black Diamond approval. Insufficient certified history returns HOLD. Nothing changes V2 weights, source workbooks, production databases or model-serving probabilities.

## Current acceptance evidence

Tests use synthetic HTTP transports, .example identities, explicitly synthetic HTML, and synthetic dated forecast rows. Real TeamRankings access in the development runtime returned HTTP 403; NBA CDN access through the research tool also returned 403. Live production extraction is not validated by those unit tests. The historical overlay lacks the certified pregame fields needed to promote it into calibration data. No real model has been calibrated by this implementation.
