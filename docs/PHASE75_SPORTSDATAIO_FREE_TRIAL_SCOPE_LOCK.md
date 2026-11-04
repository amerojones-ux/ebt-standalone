# Phase 75 — SportsDataIO Free Trial scope-contradiction lock

Status: **BLOCKED_PRECONDITION / NO LIVE REQUEST**

Phase 75 records the account's nonsecret SportsDataIO access classification as
`FREE_TRIAL` and prevents that access from being confused with production,
live, or model-eligible data.

No SportsDataIO request is executed by this phase.

## Account classification

A SportsDataIO account confirmation identifies the current access as API Free
Trial. No API key value is copied into the repository.

The committed config records:

- `declared_access_method=FREE_TRIAL`
- `account_access_confirmed=true`
- `scrambled_data_acknowledged=true`
- `trial_scope_reconciled=false`
- `official_scope_status=CONFLICTING`
- `model_evidence_allowed=false`
- network and forecast activation remain disabled

## Current official documentation conflict

Current SportsDataIO general developer pages describe Free Trial as:

- scrambled but structurally identical to production;
- intended for integration/schema testing;
- not real data and not suitable for analysis/display; and
- capable of selecting sports and feeds / all endpoints and all 13 sports.

Current NFL API endpoint documentation simultaneously states that the API Free
Trial only provides access to UEFA Champions League (Competition ID 3).

Both statements are provider-published and current. Phase 75 does not silently
choose one interpretation.

References reviewed:

- https://sportsdata.io/developers
- https://sportsdata.io/developers/apis
- https://sportsdata.io/help/scrambled-data
- https://sportsdata.io/developers/api-documentation/nfl

## Evidence boundary

Free Trial is permanently classified as scrambled integration data.

It cannot become generic model evidence even if someone manually flips
entitlement/feed/freshness flags.

`can_promote_to_model_evidence("FREE_TRIAL", ...)` remains false.

The provider's own help material states that some scores and statistics are
randomly altered from actual values. Schedules/teams/players may have different
scrambling behavior, but Phase 75 does not grant any analytic exception from
that statement.

## Probe preconditions

A SportsDataIO authenticated probe remains blocked until all of these are true:

1. Free Trial account access is confirmed.
2. Scrambled-data limitations are acknowledged.
3. The current official scope contradiction is reconciled.
4. `trial_scope_reconciled=true`.
5. The exact subscribed API product/feed is identified.
6. The exact header-auth endpoint is reviewed.
7. Request quota is reviewed.
8. Overage behavior is reviewed.

Header authentication is fixed to:

`Ocp-Apim-Subscription-Key`

Black Diamond continues to forbid query-string key authentication even though
SportsDataIO documentation also supports query keys.

## Fail-closed transition

When the current config is evaluated, the provider remains:

`BLOCKED_PRECONDITION`

If scope is reconciled and every route/quota prerequisite becomes complete
while no hardened one-shot workflow exists, the gate transitions to:

`IMPLEMENTATION_REQUIRED`

and CI fails until a reviewed one-shot workflow is installed.

This prevents account metadata edits from silently producing an executable live
path.

## Forecast/model effect

Phase 75 does not alter:

- `forecast_enabled=false`
- `network_autorun_enabled=false`
- global `SAFE_HOLD`
- SportsDataIO `live_auth_verified=false`
- SportsDataIO `entitlement_verified=false`
- SportsDataIO `identity_verified=false`
- SportsDataIO `freshness_verified=false`
- SportsDataIO `model_evidence_allowed=false`

No SportsDataIO secret was read and no SportsDataIO provider request was made.
