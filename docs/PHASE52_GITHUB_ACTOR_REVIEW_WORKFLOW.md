# Phase 52 — GitHub-actor-bound live-auth evidence review workflow

Status: **PREPARED / DEFAULT HOLD / NO PROVIDER EXECUTION**

Phase 52 replaces the preferred free-form reviewer path with a manual GitHub Actions review workflow whose reviewer identity comes from the authenticated GitHub actor.

Workflow:

`.github/workflows/provider-live-auth-evidence-review.yml`

## Inputs and default state

The workflow requires:
- provider;
- source provider-probe workflow run ID;
- decision: `HOLD`, `REJECT`, or `APPROVE`;
- explicit approval phrase for `APPROVE`.

Default decision is `HOLD`.
Default approval confirmation is `NO`.

The job runs only on `refs/heads/main`.

## Source-run validation

The source run must:
- have the exact numeric run ID requested;
- be a `workflow_dispatch` run;
- originate from `main`;
- be completed;
- conclude `success`;
- use the exact provider-specific probe workflow;
- belong to `amerojones-ux/ebt-standalone`;
- have matching repository/head-repository identity;
- expose a valid 40-character source commit.

Only the exact sanitized receipt and attestation-verification marker artifacts for that source run are accepted.

## Evidence reconstruction

The workflow retrieves GitHub artifact metadata and ZIPs, then runs the preferred repository ingestion path:

receipt artifact
+ verification-marker artifact
+ GitHub run metadata
→ attested `REVIEW_ONLY` candidate.

No provider credential or provider network is used.

## Reviewer identity

The review decision uses:

`github:<github.actor>#<github.actor_id>`

The actor value is never supplied by a workflow input.

The review decision remains non-mutating and can only produce an approved/rejected decision package.

## Review-decision provenance

The emitted `provider_review_decision.json` is:
1. signed with the pinned `actions/attest` action;
2. verified with `gh attestation verify`;
3. constrained to:
   - the authoritative repository;
   - the exact review workflow;
   - `refs/heads/main`;
   - the exact review workflow commit.

A sanitized review-attestation verification marker is generated only after successful cryptographic verification.

## Persisted review package

The workflow uploads only:
- `provider_review_candidate.json`;
- `provider_review_decision.json`;
- `provider_review_decision_attestation_verification.json`.

Retention is 7 days.

The workflow has:
- `contents: read`;
- `actions: read`;
- `id-token: write`;
- `attestations: write`;
- `artifact-metadata: write`.

It has no provider secret reference, no repository-content write permission, no Actions write permission, and no ledger/readiness mutation step.

## Boundary

Phase 53 closes this boundary: the final evidence ledger and all promotion previews now require the signed review-workflow attestation package, not merely the raw review decision.

No provider request, credential read, ledger write, readiness write, forecast activation, or wager action occurs in this phase.
