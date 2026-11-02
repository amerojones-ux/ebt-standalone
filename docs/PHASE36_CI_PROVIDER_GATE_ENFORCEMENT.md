# Phase 36 — Provider reconciliation enforced in Sports Validation CI

Status: **OFFLINE ENFORCEMENT**

The normal `Sports validation` workflow now runs the two provider safety CLIs on every supported Python runtime before the existing command-line checks:

1. `provider_contract_reconciliation_cli.py`
2. `provider_activation_gate_cli.py config/provider_readiness.json`

A pull request can no longer pass normal CI if:
- any of the seven canonical provider configs drifts from its secret mapping;
- a committed network/forecast switch is enabled;
- a guarded request counter is nonzero;
- provider coverage becomes incomplete;
- the committed global readiness config becomes invalid.

The expected committed outputs remain:
- `PROVIDER_CONTRACT_RECONCILIATION: SAFE_HOLD`
- `GLOBAL_PROVIDER_GATE: SAFE_HOLD`

These checks are offline and do not access secrets or provider networks.
