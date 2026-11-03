# Phase 68 — Manual provider workflow security parity

Status: **SAFE HOLD / OFFLINE**

Phase 68 closes the remaining control gap between the hardened live/review/promotion workflows and older manual provider-control workflows.

## Scope

The following manual workflows are brought to the same first-attempt and protected-main execution standard:

- `live-provider-approval-gate.yml`
- `provider-activation-gate.yml`
- `provider-offline-preflight.yml`
- `provider-secret-presence.yml`
- `weatherapi-execution-gate.yml`

## Common execution controls

Each workflow now requires:

- `github.run_attempt == 1`
- `github.ref_protected == true`
- `github.ref == 'refs/heads/main'`
- a pinned `ubuntu-24.04` runner
- non-cancelling workflow concurrency

The four workflows that execute repository code check out the immutable dispatch SHA:

`ref: ${{ github.sha }}`

and verify:

- `git rev-parse HEAD == GITHUB_SHA`
- a clean working tree

before executing repository Python.

## Provider secret-presence boundary

`provider-secret-presence.yml` is the only workflow in this phase that receives provider secrets.

It now requires the exact explicit authorization phrase:

`I_APPROVE_PROVIDER_SECRET_PRESENCE_CHECK`

in addition to the protected-main and first-attempt controls.

Provider secret values are no longer declared at job scope. They are materialized only in the guarded `Report presence only` step.

The step continues to emit only `PRESENT` or `MISSING_OR_DIFFERENT_NAME`; it does not print secret values and performs no provider network request.

## Regression coverage

`tests/test_provider_manual_workflow_security.py` enforces:

- manual-only execution for these control workflows;
- no schedule, push or pull-request trigger;
- protected-main and first-attempt gates;
- pinned runner and non-cancelling concurrency;
- immutable checkout and clean-tree verification where repository code is executed;
- read-only repository permissions;
- no provider secrets in offline checkout workflows;
- explicit secret-presence consent;
- step-scoped secret materialization;
- absence of obvious network clients/URLs or direct environment-value logging in the presence check.

## Boundary

Phase 68 does not validate provider credentials and does not prove provider entitlement.

It does not make provider network requests, write readiness/evidence state, activate forecasts, or execute wagers.

Global state remains `SAFE_HOLD`.
