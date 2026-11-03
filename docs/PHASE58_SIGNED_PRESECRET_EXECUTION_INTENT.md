# Phase 58 — Signed pre-secret one-shot execution intent

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER REQUEST EXECUTED**

Phase 58 hardens the final boundary before a provider credential can be exposed to a live probe step.

## Core rule

A provider secret is not made available to the probe step until the workflow has:

1. validated the pinned toolchain;
2. created a sanitized one-shot execution-intent record;
3. checksum-verified that intent;
4. signed the intent with GitHub artifact attestation;
5. verified the attestation against the exact exported bundle;
6. verified the same attestation through GitHub's attestation API.

Only after all of those steps produce:

`intent_verified=1`

may the provider-secret-bearing probe step run.

## Execution-intent contract

`provider_execution_intent.py` binds:

- provider;
- authoritative repository;
- GitHub workflow run ID;
- source commit;
- `refs/heads/main`;
- exact provider probe workflow;
- authenticated GitHub actor;
- GitHub actor ID;
- timezone-aware creation timestamp;
- exact account/plan review authorization phrase;
- exact one-request authorization phrase;
- canonical `request_plan_sha256`;
- `max_requests: 1`;
- network scope: `one-shot-authentication-probe`;
- ledger mutation disabled;
- readiness mutation disabled;
- forecast activation disabled.

The canonical intent body is SHA-256 checksum-bound.

No provider secret is present in the intent.

## Intent attestation evidence

Each prepared provider workflow now persists, after successful verification:

- `provider_execution_intent.json`;
- the exact execution-intent attestation bundle;
- a sanitized execution-intent attestation-verification marker.

The marker records:

- provider;
- repository/run/commit/ref;
- exact signer workflow;
- actor and actor ID;
- intent checksum;
- exact intent-file SHA-256;
- canonical request-plan SHA-256;
- `max_requests: 1`;
- attestation ID/URL;
- exact bundle SHA-256;
- local-bundle + GitHub-API verification modes;
- runner/toolchain fingerprint.

Retention is 7 days.

## Secret isolation

The provider API key remains scoped only to the live probe step.

CI explicitly checks that:

- no `secrets.*` reference appears before the probe step;
- the secret-bearing probe block requires:
  - pinned toolchain verification;
  - `steps.verify_intent.outputs.intent_verified == '1'`.

A generic conversation instruction such as "Proceed" is not an execution authorization and cannot satisfy the workflow's exact approval inputs.

## Registry behavior

The live-probe readiness registry now requires:

- signed pre-secret execution intent;
- dual attestation verification for that intent;
- exact intent artifact naming;
- the verified-intent gate on the live probe.

Removing or weakening any of those controls changes the provider probe status to:

`INVALID_HOLD`

## Boundary

This phase prepares and enforces authorization evidence for a future manual one-shot request. It does not dispatch a workflow, read a provider secret, call a provider endpoint, mutate the evidence/readiness ledger, activate forecasting, or place any wager.
