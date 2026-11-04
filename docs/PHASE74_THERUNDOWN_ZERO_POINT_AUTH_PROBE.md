# Phase 74 — TheRundown zero-data-point authenticated sample probe

Status: **PREPARED_DEFAULT_DENY / NO LIVE REQUEST**

Phase 74 promotes TheRundown from the Phase 73 precondition-only gate into the
same hardened signed live-auth pipeline already used by WeatherAPI, The Odds
API, and API-Sports.

No provider request is executed by this phase.

## Evidence used to define the probe

Account evidence confirms the EBT account is on TheRundown's **Free** plan.
No credential value is copied into this repository.

Current provider documentation confirms:

- Free is a $0 plan with no credit card required.
- Free is capped at 20,000 data points per UTC day and 200,000 per month.
- Free odds are delayed by five minutes.
- Free is hard-capped at its limits; it does not create automatic overage
  charges.
- `GET /api/v2/stats/sample` requires authentication and returns a fixed
  complete-game statistics sample for schema inspection at **zero data
  points**.
- The sample is not a current live game and does not establish production
  statistics coverage.

Provider references reviewed:

- https://therundown.io/free-sports-data-api
- https://therundown.io/pricing/api
- https://therundown.io/docs/quickstart

## Exact request plan

The canonical request plan is:

- method: `GET`
- scheme: `https`
- host: `therundown.io`
- path: `/api/v2/stats/sample`
- credential: header-only `X-TheRundown-Key`
- fixed header: `Accept: application/json`
- redirects: forbidden
- retries: zero
- maximum requests: one
- maximum response body: bounded in memory
- environment proxies: disabled

The API key is never placed in the URL or query string.

## Runtime authorization

A live workflow will run only when both exact phrases are selected:

`I_CONFIRM_THERUNDOWN_PLAN_DATAPOINT_QUOTA_AND_OVERAGE_REVIEWED`

`I_APPROVE_ONE_THERUNDOWN_AUTHENTICATED_SNAPSHOT_REQUEST`

The workflow is additionally restricted to:

- manual `workflow_dispatch`;
- workflow run attempt 1 only;
- protected `main` only;
- immutable dispatch commit checkout;
- pinned Python 3.13 toolchain;
- signed pre-secret execution intent; and
- global live-probe serialization.

A generic "proceed" does not authorize a request.

## PASS semantics

The only PASS category is:

`authenticated_zero_datapoint_sample_json`

It requires:

- exact endpoint identity;
- HTTP 200;
- non-empty valid JSON object/list; and
- when an `X-Datapoints` response header is present, its value must be zero.

A missing `X-Datapoints` header is not treated as proof of billing behavior;
the route's zero-data-point classification comes from the provider's documented
endpoint contract. A present nonzero value causes HOLD.

A PASS proves only that the configured key authenticated to the documented
fixed sample endpoint and returned JSON.

A PASS does **not** prove:

- current/live statistics access;
- sportsbook or market access;
- paid-plan entitlement;
- current data freshness;
- player/team identity completeness;
- historical coverage;
- commercial display rights; or
- model-evidence eligibility.

The receipt permanently records:

- `sample_only=true`
- `documented_zero_datapoint_endpoint=true`
- `model_evidence_allowed=false`

## Signed evidence chain

The workflow produces the same six evidence artifacts as the existing hardened
providers:

1. sanitized execution intent;
2. execution-intent attestation bundle;
3. execution-intent verification marker;
4. sanitized probe receipt;
5. receipt attestation bundle; and
6. receipt attestation verification marker.

Both the intent and receipt attestations are verified locally from the exact
bundle and independently through GitHub before evidence is persisted.

Generated markers are immediately self-verified before downstream gates open.

## Review and promotion integration

TheRundown is registered in:

- canonical request-plan validation;
- signed execution-intent contracts;
- receipt/attestation verification;
- GitHub artifact metadata and ZIP ingestion;
- receipt review candidates;
- reviewer decisions;
- attested review decisions;
- evidence-ledger signer policy;
- the manual evidence-review workflow; and
- the provider probe readiness registry.

A reviewed successful receipt may therefore promote only
`TheRundown.live_auth_verified=true`.

The global state must remain `SAFE_HOLD`, with:

- `forecast_enabled=false`;
- `network_autorun_enabled=false`;
- `entitlement_verified=false`;
- `identity_verified=false`;
- `freshness_verified=false`; and
- `model_evidence_allowed=false`.

## Remaining provider blockers

After Phase 74, the Phase 73 fail-closed precondition gate continues to cover:

- SportsDataIO
- Sportradar
- RapidAPI

Those providers remain non-executable until their exact account/product/route
and billing prerequisites are established.

No TheRundown request, secret read, readiness mutation, or forecast activation
was performed while installing Phase 74.
