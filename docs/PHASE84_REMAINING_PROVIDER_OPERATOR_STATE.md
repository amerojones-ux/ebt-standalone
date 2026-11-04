# Phase 84 — Deterministic remaining-provider operator state

Status: **OFFLINE STATUS CONTROL / NO PROVIDER REQUEST / SAFE_HOLD**

Phase 84 turns the remaining provider path into a machine-verifiable state
machine instead of relying on narrative handoffs.

The engine reads only committed redacted repository state.

It never:

- reads provider secrets;
- contacts provider networks;
- authorizes requests;
- enables forecasting;
- enables model evidence;
- enables network autorun; or
- mutates provider configuration.

## Engine

`provider_remaining_operator_state.py`

The engine evaluates:

- `config/provider_readiness.json`
- `config/provider_account_evidence.json`
- SportsDataIO operational config
- Sportradar operational config
- RapidAPI operational config
- presence of Phase 80 metadata-claim workflows
- presence of future hardened one-shot provider probe workflows

It reuses existing account-registry and account/config consistency validation.

## Current committed state

At Phase 84 creation:

- overall providers: 7
- persisted live-auth verified: 4
- unresolved providers: 3
- unresolved providers with live-auth verified: 0
- global forecast enabled: false
- global network autorun enabled: false

The unresolved providers are:

- SportsDataIO
- Sportradar
- RapidAPI

All three currently resolve to:

`ACCOUNT_METADATA_REQUIRED`

The legal next stage is:

`SIGNED_ACCOUNT_METADATA_CLAIM`

using the appropriate Phase 80 manual workflow.

No hardened one-shot probe workflow exists for these three providers yet, and
that is intentional.

## State machine

### ACCOUNT_METADATA_REQUIRED

Used when required exact provider account metadata is still missing.

Next legal stage:

`SIGNED_ACCOUNT_METADATA_CLAIM`

The engine points to the corresponding provider-specific Phase 80 workflow.

Provider network requests remain blocked.

### METADATA_PERSISTED_PROBE_ENGINEERING_REQUIRED

Used after exact source-verified account metadata has been promoted into
committed state, but before a hardened provider-specific one-shot probe
workflow exists.

Next legal stage:

`HARDENED_ONE_SHOT_PROBE_ENGINEERING`

No provider request is authorized.

### PROBE_PREPARED_AWAITING_EXPLICIT_AUTHORIZATION

Used only when:

- account metadata is complete;
- committed account/config state is consistent;
- a hardened provider-specific probe workflow exists; and
- live-auth is still not verified.

Next legal stage:

`EXPLICIT_ONE_SHOT_REQUEST_AUTHORIZATION`

Even here, the engine keeps `provider_network_request` in the blocked-action
list because a fresh provider-specific authorization must still be supplied for
the actual one-shot request.

### LIVE_AUTH_VERIFIED

Used only when committed live-auth evidence says the provider is verified and
the required account metadata is complete.

A live-auth-verified state does not create standing permission for another
provider request.

Fresh request authorization is still required for any future provider network
operation.

### INVALID_HOLD

Used whenever committed state is contradictory or unsafe.

Examples include:

- live-auth verified while required account metadata is incomplete;
- provider network enabled unexpectedly;
- forecast enabled unexpectedly;
- account/config consistency failure;
- missing Phase 80 metadata workflow;
- unexpected entitlement/identity/freshness activation; or
- unexpected model-evidence permission.

## Provider-specific metadata completeness

### SportsDataIO

Requires persisted proof of:

- reconciled official scope;
- exact product;
- exact feed;
- quota review;
- overage review;
- exact HTTPS v3 probe endpoint; and
- fail-closed network/forecast/model-evidence flags.

### Sportradar

Requires persisted proof of:

- exact NFL product;
- package;
- trial or production access level;
- subscription/product inventory;
- quota/QPS review;
- exact derived League Hierarchy endpoint; and
- fail-closed network/forecast flags.

### RapidAPI

Requires persisted proof of:

- exact subscribed API product;
- exact `X-RapidAPI-Host`;
- pricing type;
- exact plan;
- billing object;
- quota review;
- overage review;
- exact HTTPS host-matching endpoint; and
- fail-closed network/forecast flags.

## CLI

`provider_remaining_operator_state_cli.py`

The CLI emits deterministic JSON.

It exits nonzero only for `INVALID_HOLD`.

This allows normal SAFE_HOLD transitions—such as metadata becoming complete
or a hardened probe being installed—to pass CI without weakening any gate.

## CI enforcement

The protected Sports validation workflow now runs:

`python provider_remaining_operator_state_cli.py`

after account-evidence consistency validation.

Every future PR therefore must preserve a valid remaining-provider operator
state on both required Python versions:

- validation (3.11)
- validation (3.13)

## Signed operator-state workflow

`.github/workflows/provider-remaining-operator-state.yml`

The workflow is:

- manual only;
- protected-main only;
- first-attempt only;
- read-only for repository contents;
- secret-free;
- provider-network-free; and
- non-mutating.

It creates:

`remaining_provider_operator_state.json`

and requires every remaining provider to keep
`provider_network_request` blocked.

The status file is GitHub-attested and independently verified against:

- this repository;
- the exact signer workflow;
- protected main; and
- the exact source commit.

The signed two-file package is retained for seven days.

## Operational consequence

The system no longer needs a human-readable handoff to decide whether the next
step is:

- collect account metadata;
- engineer a probe;
- request exact one-shot authorization; or
- HOLD because repository state is invalid.

That decision is now derived from committed evidence.

The current machine-derived result remains:

**SAFE_HOLD — 4/7 live-auth verified; SportsDataIO, Sportradar and RapidAPI
require exact provider account metadata before probe engineering or any
provider request.**
