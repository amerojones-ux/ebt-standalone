# Phase 79 — Non-mutating provider account-metadata transition preview

Status: **PROPOSAL_ONLY / NO LIVE REQUEST**

Phase 79 adds a deterministic transition engine for the three unresolved
providers. It is designed for the point when account-portal or provider-support
facts become available.

The engine does not collect those facts itself. It does not browse an account,
read credentials, execute provider requests, write config files, or enable
forecasting.

## Accepted evidence source classes

A transition may be proposed only from:

- `ACCOUNT_PORTAL`
- `PROVIDER_SUPPORT`

Generic web search, old project assumptions, account registration alone, and
ambiguous user wording are not sufficient to mark account-specific product or
route facts verified.

## Global output boundary

Every valid transition preview permanently returns:

- `write_permitted=false`
- `network_request_permitted=false`
- `forecast_activation_permitted=false`
- `model_evidence_allowed=false`

The result is a candidate state for review, not an applied state.

The generated candidate must pass:

1. the Phase 78 redacted account-evidence registry validator;
2. the transitioned provider's offline contract; and
3. the Phase 78 account-evidence ↔ operational-config consistency validator.

If any layer disagrees, the transition returns HOLD.

## SportsDataIO

Required account/support facts:

- scope explicitly reconciled;
- exact product;
- exact feed/scope;
- exact HTTPS v3 endpoint;
- quota reviewed;
- overage behavior reviewed.

A Free Trial proposal remains:

- scrambled-data only;
- `model_evidence_allowed=false`;
- `network_enabled=false`;
- `forecast_enabled=false`.

The engine will not silently convert the current provider-documentation
conflict into RECONCILED. The facts must explicitly state that provider/account
support resolved it.

## Sportradar

Required account/support facts:

- product explicitly identifies NFL;
- exact package name;
- access level is exactly `trial` or `production`;
- quota/QPS reviewed.

The engine derives, rather than accepts, the League Hierarchy route:

`https://api.sportradar.com/nfl/official/{access_level}/v7/en/league/hierarchy.json`

This prevents a copied account value from being paired with a mismatched trial
or production URL.

The proposal still keeps:

- `quota_impact_approved=false`;
- `network_enabled=false`;
- request count zero; and
- forecasting disabled.

## RapidAPI

Phase 79 closes a schema gap: the operational RapidAPI config now persists the
exact reviewed `probe_endpoint`, not only an `endpoint_reviewed` boolean.

Required account/support facts:

- exact subscribed API product;
- exact `X-RapidAPI-Host`;
- pricing type;
- plan name;
- billing object;
- exact HTTPS endpoint matching that host;
- quota reviewed;
- overage behavior reviewed.

The engine rejects ambiguous product names including:

- `all`
- `sports`
- `api`
- `unknown`
- `any`

The endpoint must:

- use HTTPS;
- match the verified host;
- contain a non-root path;
- contain no userinfo;
- contain no explicit port;
- contain no query string; and
- contain no fragment.

This prevents an endpoint review flag from existing without the exact route it
describes and prevents credential-bearing query strings from becoming the
canonical probe route.

## Sensitive input boundary

The transition engine accepts only provider-specific fact keys.

Unexpected fields are rejected. Text values resembling credential material are
rejected. No API-key, token, password, authorization header, email address, or
account ID belongs in transition facts or generated evidence.

## Review sequence

When verified account facts are later available:

1. build the non-mutating transition preview;
2. review the exact account-registry changes;
3. review the exact operational-config changes;
4. run full protected CI;
5. merge only through protected main;
6. only then implement or enable a hardened one-shot provider workflow;
7. obtain fresh provider-specific request authorization before any network
   request.

Phase 79 itself performs none of steps 6–7.

## Current provider state remains unchanged

SportsDataIO remains blocked on the unresolved scope conflict and exact
feed/quota facts.

Sportradar remains blocked on actual NFL package, access level, and quota.

RapidAPI remains blocked on the exact subscribed product/host/plan/billing
route.

No live request is authorized or performed by Phase 79.
