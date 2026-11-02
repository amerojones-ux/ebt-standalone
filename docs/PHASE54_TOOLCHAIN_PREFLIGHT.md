# Phase 54 — Pin the live-probe execution environment and gate provider access on toolchain preflight

Status: **PREPARED_DEFAULT_DENY / NO LIVE PROVIDER EXECUTION**

The prepared provider probes previously depended on the moving `ubuntu-latest` image, ambient `python3`, and whatever GitHub CLI version happened to be installed. Phase 54 narrows that execution drift before any provider request can run.

## Runner and Python pinning

Each manual probe now uses:

- runner: `ubuntu-24.04`
- official `actions/setup-python` v7.1.0 pinned to immutable commit:
  `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`
- Python: exactly `3.13`
- `check-latest: false`

The setup action is pinned by commit SHA rather than a floating tag.

## Toolchain preflight

A preflight step runs before the provider request and must prove:

- Python runtime is 3.13;
- `gh` is installed;
- `gh attestation verify --help` succeeds;
- the CLI exposes every flag required by the provenance policy:
  - `--bundle`
  - `--repo`
  - `--signer-workflow`
  - `--source-ref`
  - `--source-digest`
  - `--format`

Only then is:

`toolchain_verified=1`

written to the step output.

The provider probe step itself is explicitly gated by:

`if: steps.toolchain.outputs.toolchain_verified == '1'`

If the toolchain preflight fails or the CLI semantics drift enough to remove a required flag, the provider request is skipped.

## Timeout

The job timeout is increased from 2 to 5 minutes. This remains tightly bounded while allowing realistic time for:

- pinned Python setup;
- one provider request;
- signed attestation generation;
- exact-bundle verification;
- GitHub-API verification;
- three short-lived artifact uploads.

## CI enforcement

The standard security tests and probe-readiness registry now require:

- `ubuntu-24.04`;
- the exact setup-python commit;
- Python 3.13;
- `check-latest: false`;
- the toolchain step;
- the required attestation CLI flags;
- the explicit toolchain gate on the provider request.

The expected registry state remains `PREPARED_DEFAULT_DENY`.

No provider request, secret access, readiness mutation, evidence promotion, or forecast activation occurs in this phase.
