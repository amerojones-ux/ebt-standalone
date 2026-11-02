# Phase 33 — Global provider + model activation gate

Status: **SAFE HOLD / NO LIVE ACTIVATION**

All seven configured providers now have provider-specific contracts, but successful provider authentication alone is not sufficient to activate Black Diamond forecasting.

This phase adds a single offline activation gate that combines provider readiness with model-level certification.

## Provider readiness
A provider can satisfy a required role only after its contract, live authentication, entitlement and freshness are verified. Stats providers additionally require identity verification and explicit permission to act as model evidence.

Market-comparison providers may be operational while remaining permanently barred from increasing forecast probabilities or calibration.

RapidAPI remains `aggregator_unresolved` until an exact underlying API product/host is selected.

## Model-level gates
Even if all required providers are ready, activation remains blocked until all four are independently verified:
1. source provenance;
2. roster/injury identity;
3. historical calibration;
4. joint dependence/correlation validation.

The committed config has no required provider set, all live verification flags false, all model gates false, network autorun false and forecast_enabled false. Its expected result is `SAFE_HOLD`.

The module can report only `ELIGIBLE_FOR_MANUAL_ACTIVATION_REVIEW`; it never turns forecasting on itself.

No API call, credential read, wager action or production activation occurs in this phase.
