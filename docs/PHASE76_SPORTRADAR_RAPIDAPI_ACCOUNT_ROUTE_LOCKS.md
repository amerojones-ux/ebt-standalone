# Phase 76 — Sportradar and RapidAPI account/route provenance locks

Status: **BLOCKED_PRECONDITION / NO LIVE REQUEST**

Phase 76 distinguishes account existence from provider-product entitlement for
Sportradar and RapidAPI.

No provider secret is read and no provider request is performed.

## Sportradar

Nonsecret account evidence confirms that a Sportradar account exists. It does
not establish:

- an NFL API subscription/package;
- whether the key is Trial or Production;
- the account's configured 30-day quota;
- the product's QPS limit; or
- the exact access-level URL that matches the key.

The committed config therefore records:

- `account_registration_confirmed=true`
- `subscription_details_verified=false`
- `product_inventory_verified=false`
- `access_level_verified=false`
- `access_level=UNKNOWN`
- `product_verified=false`
- `quota_reviewed=false`

Current Sportradar documentation requires `x-api-key` authentication and says
the `access_level` URL segment must be `trial` or `production` matching
the key. Subscription packages and product-specific quota/QPS are viewable in
the account.

The intended NFL League Hierarchy endpoint remains:

`https://api.sportradar.com/nfl/official/{access_level}/v7/en/league/hierarchy.json`

No endpoint is committed until the actual account subscription establishes the
correct access level and NFL package.

References reviewed:

- https://developer.sportradar.com/football/docs/nfl-ig-api-basics
- https://developer.sportradar.com/football/reference/nfl-league-hierarchy
- https://developer.sportradar.com/getting-started/docs/your-account
- https://developer.sportradar.com/getting-started/docs/authentication

## RapidAPI

Nonsecret account evidence confirms a RapidAPI sign-in exists. It does not
establish any subscribed sports API product.

The committed config therefore records:

- `account_signin_confirmed=true`
- `subscription_inventory_verified=false`
- `route_binding_verified=false`
- exact API product blank
- exact `X-RapidAPI-Host` blank
- pricing type unknown
- plan name blank
- billing object blank
- subscription/quota/overage/endpoint verification false

RapidAPI documentation states that:

- `X-RapidAPI-Key` identifies the app/context;
- `X-RapidAPI-Host` uniquely identifies the API being called;
- both headers are required for Rapid Runtime APIs; and
- usage/billing/rate limits are tied to the subscribed plan and billing object.

A generic RapidAPI key is therefore never sent to a guessed or user-supplied
host.

References reviewed:

- https://docs.rapidapi.com/v2/docs/configuring-api-authentication
- https://docs.rapidapi.com/v2/docs/api-pricing

## Fail-closed provider gates

Sportradar remains blocked until all of the following are verified:

1. product subscription details;
2. subscribed product inventory;
3. access level from the account;
4. exact NFL product/package;
5. quota/QPS review; and
6. access-level-specific League Hierarchy endpoint.

RapidAPI remains blocked until all of the following are verified:

1. subscription inventory;
2. exact API product;
3. exact `X-RapidAPI-Host`;
4. product-to-host binding;
5. pricing type;
6. plan name;
7. billing object;
8. subscription status;
9. quota and overage behavior; and
10. exact endpoint.

When all prerequisites become complete while no hardened one-shot workflow
exists, CI transitions the provider to `IMPLEMENTATION_REQUIRED` rather than
silently permitting execution.

## Safety invariants

Phase 76 does not change:

- `forecast_enabled=false`
- `network_autorun_enabled=false`
- global `SAFE_HOLD`
- Sportradar `live_auth_verified=false`
- RapidAPI `live_auth_verified=false`
- any provider `model_evidence_allowed=false`

Account registration/sign-in alone is explicitly insufficient for provider
readiness.
