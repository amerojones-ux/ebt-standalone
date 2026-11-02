# Phase 35 — Seven-provider contract reconciliation

Status: **SAFE HOLD / OFFLINE**

All seven canonical provider IDs now have machine-readable configuration files:

- TheRundown
- SportsDataIO
- The Odds API
- API-Sports
- RapidAPI
- WeatherAPI
- Sportradar

This phase adds a single offline reconciliation pass that checks:

1. exact one-to-one coverage with `provider_preflight.PROVIDERS`;
2. exact GitHub secret-name mapping;
3. expected provider identity label;
4. every committed network toggle remains false;
5. every committed forecast toggle remains false;
6. provider-specific request counters remain integer zero;
7. provider-specific approval switches that must remain disabled are false.

The Odds API and API-Sports now have dedicated machine-readable hold configs, closing the previous gap where their executable probe code existed without matching provider config state.

Expected committed result:

`PROVIDER_CONTRACT_RECONCILIATION: SAFE_HOLD`

This reconciliation does not read any secret, make any provider request, or change the global activation status.
