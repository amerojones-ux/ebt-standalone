# Phase 71 — Promotion PR handoff outside GitHub Actions

Status: **SAFE_HOLD / operational repair**

The Phase 70 apply workflow correctly verified the signed WeatherAPI promotion,
attested the apply manifest, and created the isolated promotion branch. GitHub
then returned HTTP 403 when the workflow attempted to open a pull request because
this repository does not allow GitHub Actions itself to create or approve pull
requests.

Phase 71 removes that avoidable failure mode without weakening repository
protection.

## New behavior

The controlled promotion apply workflow now:

1. re-verifies the signed promotion preview;
2. rebuilds the exact SAFE_HOLD promotion;
3. attests and verifies the apply manifest;
4. creates the isolated promotion branch;
5. updates only the two generated provider config files on that branch;
6. reports the branch name in the workflow summary; and
7. exits successfully.

The workflow intentionally does **not** open or merge a pull request.

## PR handoff

An authorized external GitHub client, such as the connected GitHub integration,
may review the exact branch diff and open the PR against protected `main`.

That PR must still satisfy the repository ruleset and required validation checks.

## Security effect

This removes the need to enable the repository setting that would allow GitHub
Actions to create or approve pull requests.

The workflow no longer requests `pull-requests: write`.

It retains:

- protected-main execution;
- first-attempt-only execution;
- signed-preview verification;
- exact apply attestation;
- no provider secrets;
- no provider network requests;
- `SAFE_HOLD`;
- `forecast_enabled=false`;
- `network_autorun_enabled=false`; and
- no automatic merge.
