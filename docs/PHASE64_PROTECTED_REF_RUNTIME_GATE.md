# Phase 64 — Protected-reference runtime execution gate

Status: **SAFE HOLD / OFFLINE**

Phase 64 makes repository-governance uncertainty fail closed at the live-provider boundary.

## Governance evidence

The connected GitHub integration reports no repository rulesets for `amerojones-ux/ebt-standalone`.

The classic branch-protection endpoint is not readable through this integration, so the current external protection state of `main` cannot be independently certified from this session.

Rather than assume protection exists, the live-provider workflows now require GitHub's runtime protected-reference signal.

## Runtime gate

WeatherAPI, The Odds API and API-Sports require:

`github.ref_protected == true`

at the job gate, together with:

- `github.run_attempt == 1`
- `github.ref == 'refs/heads/main'`
- the exact provider-specific review phrase
- the exact one-request authorization phrase

If GitHub does not consider the dispatched `main` ref protected, the live-probe job does not start.

That occurs before checkout, execution-intent creation, provider secret exposure or network execution.

## Readiness enforcement

The offline prepared-probe registry treats the protected-reference runtime gate as mandatory.

Removing or weakening the gate changes that provider from `PREPARED_DEFAULT_DENY` to `INVALID_HOLD`.

Regression tests explicitly replace the protected-ref requirement with a false condition and require fail-closed readiness.

## Layered authorization chain after Phase 64

manual exact dispatch authorization
-> protected `main` required at runtime
-> first workflow attempt only
-> global cross-provider serialization
-> immutable dispatch-commit checkout
-> verified clean source tree
-> signed pre-secret execution intent
-> exact one-request plan
-> one provider request
-> receipt directly bound to signed intent
-> signed receipt and intent artifacts
-> REVIEW_ONLY
-> signed reviewer decision
-> evidence-ledger preview
-> global SAFE_HOLD remains independent.

## Boundary

Phase 64 does not create branch protection or repository rules.

It requires GitHub to report that protection already applies before live-provider execution is permitted.

No live provider workflow was dispatched, no provider secret was read, no provider request was performed, no forecast was activated and no wager action exists.
