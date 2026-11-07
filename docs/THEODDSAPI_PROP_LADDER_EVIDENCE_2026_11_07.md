# The Odds API prop-ladder evidence review — 2026-11-07

Scope: sanitized account-plan and public provider capability evidence only. No API key, credential value, private email address, or account identifier is stored here.

## Verified

- Account-plan evidence reviewed out-of-band confirms the configured account is on the provider's Starter plan with a 500-credit monthly allowance and $0 monthly price.
- Current provider documentation states the Starter plan includes all sports, most bookmakers and all betting markets.
- Current provider sport documentation states current odds are available on all usage plans for NBA, NFL, NHL, MLB, NCAAB and NCAAF.
- Player props and alternate/milestone markets use the per-event odds endpoint.
- Event-market discovery returns recently seen market keys by bookmaker and is not the provider's global supported-market catalog.
- The event-odds response exposes market-level last_update and player name in outcome description fields.
- Usage cost for current additional-market calls depends on markets/regions; the runtime must read response quota headers and never assume remaining quota.

## Still HOLD

- No live per-event player-prop request was executed by this change.
- Canonical provider event/player identity reconciliation is not yet verified.
- Current response freshness has not yet been independently verified.
- No real event has yet passed the posted-ladder completeness receipt.
- Network and forecast use remain disabled.
- Provider entitlement does not establish positive EV, calibrated probability, candidate qualification or wager approval.

## Activation sequence

1. Preserve projection-before-market separation.
2. Resolve provider event/team/player identity to canonical IDs.
3. Execute one bounded, explicitly authorized live event-markets discovery request.
4. Execute the smallest bounded event-odds prop request consistent with reviewed quota.
5. Validate quota headers, capture timestamps and market-level last_update.
6. Run posted-ladder coverage reconciliation.
7. Only then consider freshness/sample promotion; per-event completeness remains mandatory at runtime.
