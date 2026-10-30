# Seven-provider secure research gateway (development only)

This branch adds `extensions/provider_gateway.py` and synthetic tests for seven configured services: TheRundown, SportsDataIO (sportsdata), The Odds API, API-Sports, RapidAPI, weather, Sportradar. It **does not call any API**, authenticate any key, check subscription coverage, approve data rights, ingest historical records, certify forecasts, or place wagers.

## Secure setup
Set these names as **secret values in your own trusted backend/CI secret store**: `EBT_THERUNDOWN_API_KEY`, `EBT_SPORTSDATA_API_KEY`, `EBT_THEODDS_API_KEY`, `EBT_APISPORTS_API_KEY`, `EBT_RAPIDAPI_API_KEY`, `EBT_WEATHER_API_KEY`, `EBT_SPORTRADAR_API_KEY`. Do not paste key values into GitHub issues, commits, logs, pull requests or chat. Do not put keys in client/mobile code or public CI build output. Rotate any leaked key.

## Validation sequence (not yet performed)
1. Operator independently verifies each provider's license and entitlements for model use, historic access, retention and derived analytics; document agreement references privately. Do not assume access rights from presence of a key.
2. On an approved private runner, run provider-specific read-only identity/coverage/entitlement probes using documented endpoints, TLS validation, request deadlines, safe retries and rate limits. No secrets in URL/query, exceptions or logs. Mark VERIFIED only after successful authenticated response and independent rights review.
3. Normalize canonical league/event/team/player IDs and reconcile to official sources. Use `validate_observation` for strict required-field, status and timestamp checks. It does not independently prove canonical identity, license, completeness or data authenticity.
4. Run `python -m unittest discover -v` and CI on a review branch. Synthetic tests are not live API tests.
5. Build separately reviewed provider adapters and permitted history ingestion; immutable as-of data, leakage-free backtests and V7.1 three-engine Monte Carlo remain release prerequisites.

## Hard gates
- No automatic activation from `credential_presence`, `inventory` or `assess_provider`; those are local configuration diagnostics, not production approval.
- `assess_provider` accepts *caller-supplied* rights and feed booleans. Those booleans are not trustworthy unless independently verified by a separate approval workflow.
- Never send a market line to an independent forecast model as a feature.
- All research observations return `forecast=HOLD` and `wager=NOT APPROVED`.
- This public repository must not contain actual API keys, paid historical data or private license agreements.

Related issue: #8.
