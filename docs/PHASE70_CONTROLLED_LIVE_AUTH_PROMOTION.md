# Phase 70 — Controlled live-auth promotion

Status: **SAFE_HOLD / promotion mechanism prepared**

Phase 70 adds the final controlled persistence path for a provider that has already passed:

1. one-shot live authentication;
2. signed execution-intent verification;
3. sanitized receipt verification;
4. signed evidence review approval; and
5. signed promotion preview.

## Authorization

The apply workflow is manual and default-deny.

It requires the exact phrase:

`I_APPROVE_LIVE_AUTH_PROMOTION_APPLY`

A generic instruction does not authorize promotion.

## What the workflow may change

The workflow reconstructs the signed promotion against the current committed readiness and evidence files.

It permits exactly the previously reviewed `live_auth_verified` promotion for one provider.

It generates:

- the updated evidence ledger;
- the updated provider readiness file; and
- a sanitized apply manifest.

The apply manifest is attested and independently verified before any repository write.

## Protected-main control

The workflow never writes directly to `main`.

It creates a dedicated promotion branch, updates only:

- `config/provider_evidence.json`
- `config/provider_readiness.json`

and opens a pull request targeting `main`.

The repository's active branch ruleset then requires the normal Sports validation checks before the PR can merge.

No automatic merge is performed.

## Safety invariants

The promotion must remain:

- `global_provider_gate = SAFE_HOLD`
- `forecast_enabled = false`
- `network_autorun_enabled = false`
- `forecast_activation_permitted = false`
- `provider_network_request_permitted = false`

The workflow contains no provider API secrets and performs no provider request.

If the current committed configs drift from the signed promotion preview, the apply fails closed and does not open a pull request.
