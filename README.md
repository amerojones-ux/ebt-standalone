# EBT.ai Black Diamond Sports Analytics

Dedicated sports analytics repository, separate from credit engineering. This initial branch contains an offline validation harness, not an activated forecasting platform.

## Run

Python 3.11+ on Linux; standard library only.

```sh
python3 -m unittest -v
python3 ebt_cli.py --help
```

Validation includes strict/inclusive settlement, directional cushion, evidence-completeness gates, matching quote and EV checks, temporal holdout scoring and local hash-linked audit appends. All unit fixtures are synthetic. Caller assertions and hashes are not independently authenticated. Passing tests does not validate forecast accuracy or production readiness.

TeamRankings is the primary team-level statistical hub. Official league evidence governs schedules, roster identity and participation. Market prices are compared only after an independent model is locked; they never validate the forecast.

V2 screen estimates and conditional posterior quantiles remain research. Validated Black Diamond forecast grading requires calibrated probability >=87%, lower bound >=80%, positive central/adverse cushion and all predeclared evidence/stress/scenario gates. Wager approval separately requires verified current operator terms and positive EV. No real candidate is approved here.

No production/database/credit-platform changes, external messages, wagering or automated deployment are included. Existing source workbooks, historical records and account data remain outside this public repository. Source-ingestion adapters, fitted model, independent evidence verification, calibration and prop cards are pending implementation.
