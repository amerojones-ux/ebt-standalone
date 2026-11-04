# Phase 73 — Remaining provider precondition gates

Status: **SAFE_HOLD / NO LIVE REQUEST**

Phase 73 adds a fail-closed preparation layer for the four providers that do
not yet have hardened one-shot live-auth workflows:

- TheRundown
- SportsDataIO
- Sportradar
- RapidAPI

The goal is to prevent key presence, HTTP success, or an incomplete account
profile from being confused with production-ready provider evidence.

## Current disposition

### TheRundown — BLOCKED_PRECONDITION

The v2 reference endpoints `/api/v2/sports` and `/api/v2/affiliates`
work without a key, so they cannot prove authentication. Authenticated event
snapshots are metered in data points. Before a probe can be implemented the
exact account plan, delay, data-point quota, and overage behavior must be
reviewed.

### SportsDataIO — BLOCKED_PRECONDITION

Header authentication is fixed to `Ocp-Apim-Subscription-Key`; query-string
keys remain forbidden by Black Diamond. The exact access mode, API product,
header-auth endpoint, quota, and overage behavior must be identified before a
probe can be implemented.

A successful request is not enough to promote SportsDataIO data into model
evidence because Free Trial/Dev Key/Replay/Discovery/Production modes have
materially different freshness and truth characteristics.

### Sportradar — BLOCKED_PRECONDITION

NFL v7 uses `x-api-key`. The intended first probe remains League Hierarchy:

`https://api.sportradar.com/nfl/official/{access_level}/v7/en/league/hierarchy.json`

The account must first establish whether the key is `trial` or `production`,
confirm the NFL product/package, review rolling quota/QPS, and bind the exact
access-level-specific endpoint. The two access levels are not interchangeable.

### RapidAPI — BLOCKED_PRECONDITION

RapidAPI authentication requires both `X-RapidAPI-Key` and
`X-RapidAPI-Host`. A RapidAPI key alone does not identify the underlying
sports API. Exact product, host, plan, pricing type, billing object, quota,
overage behavior, subscription, and endpoint must all be reviewed before a
provider-specific probe may be implemented.

## CI behavior

`remaining_provider_probe_preconditions_cli.py` is now a required validation
step.

The committed state must be `BLOCKED_SAFE`.

If any provider's prerequisites become complete before a hardened one-shot
workflow is implemented and registered, the gate returns
`IMPLEMENTATION_REQUIRED` and CI fails. This prevents a configuration edit
from silently creating an executable live path.

Any mutation of network/forecast safety fields returns `INVALID_HOLD`.

## Planned provider-specific authorization phrases

No phrase below is active authorization by itself. They are reserved for future
hardened workflows after account prerequisites pass.

- TheRundown:
  - `I_CONFIRM_THERUNDOWN_PLAN_DATAPOINT_QUOTA_AND_OVERAGE_REVIEWED`
  - `I_APPROVE_ONE_THERUNDOWN_AUTHENTICATED_SNAPSHOT_REQUEST`
- SportsDataIO:
  - `I_CONFIRM_SPORTSDATAIO_ACCESS_TIER_FEED_AND_QUOTA_REVIEWED`
  - `I_APPROVE_ONE_SPORTSDATAIO_AUTHENTICATED_REQUEST`
- Sportradar:
  - `I_CONFIRM_SPORTRADAR_NFL_ACCESS_LEVEL_PRODUCT_AND_QUOTA_REVIEWED`
  - `I_APPROVE_ONE_SPORTRADAR_NFL_HIERARCHY_REQUEST`
- RapidAPI:
  - `I_CONFIRM_RAPIDAPI_PRODUCT_HOST_PLAN_QUOTA_AND_OVERAGE_REVIEWED`
  - `I_APPROVE_ONE_RAPIDAPI_PROVIDER_REQUEST`

No provider secret was read and no provider network request was made in Phase 73.
