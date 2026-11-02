# Manual provider-secret presence gate

Workflow: `Provider secret presence (manual, no network)`.

This workflow **does not** contact API vendors, validate key values, make paid calls, or activate forecasts. It prints only `PRESENT` or `MISSING_OR_DIFFERENT_NAME` for seven *proposed* secret names. GitHub secret names may differ from those configured by the operator; a missing status is not proof that the credential does not exist.

| Provider | Proposed GitHub Actions secret |
|---|---|
| TheRundown | `THERUNDOWN_API_KEY` |
| SportsData | `SPORTSDATA_API_KEY` |
| The Odds API | `THE_ODDS_API_KEY` |
| API-Sports | `API_SPORTS_API_KEY` |
| RapidAPI | `RAPIDAPI_KEY` |
| WeatherAPI | `WEATHERAPI_KEY` |
| Sportradar | `SPORTRADAR_API_KEY` |

Before running, privately reconcile names with the actual repository Actions secret inventory. Never paste credentials into issues, PRs, logs, chat, or this public repository.

Manual run after merge: GitHub repository > Actions > Provider secret presence (manual, no network) > Run workflow. Review the status-only logs. A passing presence result is **not** endpoint acceptance. Future live probes require separate reviewed endpoint contracts, rate budgets, no unexpected billable calls, response redaction, and explicit execution approval.

Forecast and wager approval remain HOLD.
