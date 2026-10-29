# EBT.ai Black Diamond Sports Analytics

Dedicated sports analytics repository, separate from credit engineering. This initial branch contains an offline validation harness, not an activated forecasting platform.

## Run

Python 3.11+ on Linux; standard library only.

```sh
python3 -m unittest -v
python3 ebt_cli.py --help
```

GitHub Actions runs the synthetic regression suite on Python 3.11 and 3.13 for pull requests and branch pushes. Its token is read-only, checkout credentials are not persisted, and both action dependencies are pinned to verified commit SHAs. No secrets, forecast schedules or deployments are used.

Approval thresholds, probability reconciliation and EV comparisons use decimal/rational arithmetic to avoid floating-point rounding at qualification boundaries. CLI JSON rejects duplicate keys and nonfinite constants. A successful command exit means the requested review ran; inspect each record's HOLD/REJECT/approval result rather than treating exit zero as approval.

JSON decimal tokens retain their precision from ingestion through qualification. Operator quotes require `quoted_at` (effective observation/publication time) and `retrieved_at` separately; rereading an old quote does not refresh its validity. Unknown effective times remain pending. CSV archive review rejects duplicate columns, malformed row widths and blank identity fields; source URLs and outcome labels remain unverified claims.

Validation includes strict/inclusive settlement, directional cushion, evidence-completeness gates, matching quote and EV checks, temporal holdout scoring and local hash-linked audit appends. All unit fixtures are synthetic. Caller assertions and hashes are not independently authenticated. Passing tests does not validate forecast accuracy or production readiness.

TeamRankings is the primary team-level statistical hub. Official league evidence governs schedules, roster identity and participation. Market prices are compared only after an independent model is locked; they never validate the forecast.

V2 screen estimates and conditional posterior quantiles remain research. Validated Black Diamond forecast grading requires calibrated probability >=87%, lower bound >=80%, positive central/adverse cushion and all predeclared evidence/stress/scenario gates. Wager approval separately requires verified current operator terms and positive EV. No real candidate is approved here.

No production/database/credit-platform changes, external messages, wagering or automated deployment are included. Existing source workbooks, historical records and account data remain outside this public repository. This research code still requires live provider acceptance, independent evidence verification, a validated fitted model and prop-card integration.

## Evidence ingestion

`python3 ebt_cli.py evidence --help` exposes an offline captured-source manifest review. It checks source-domain policy, explicit expected-field coverage, timestamp/cutoff/freshness rules, local raw-capture hashes, metric units/windows, source conflicts and official OUT status. It preserves all valid source snapshots and holds missing/rejected/conflicting fields. These checks do not establish source truth or approve a forecast. See [the schema and limitations](docs/EVIDENCE_INGESTION.md).

## Collection, extraction and calibration

`collect`, `extract` and `calibrate` CLI commands provide a bounded public-source collector, capture-bound TeamRankings/NBA extraction, and a temporal isotonic calibration assessment. Access denials, parse ambiguity and insufficient certified history remain HOLD. These adapters do not yet form an independently verified live forecasting pipeline. See [supported endpoints, usage and acceptance limits](docs/COLLECTION_CALIBRATION.md).
