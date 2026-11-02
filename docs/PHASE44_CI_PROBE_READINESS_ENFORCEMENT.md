# Phase 44 — Probe readiness registry enforced in standard CI

Status: **OFFLINE ENFORCEMENT**

The normal `Sports validation` workflow now runs:

1. seven-provider contract reconciliation;
2. global provider/model `SAFE_HOLD`;
3. prepared live-probe readiness registry.

The third check requires:

`PROBE_READINESS_REGISTRY: PREPARED_DEFAULT_DENY`

for WeatherAPI, The Odds API and API-Sports.

A future pull request therefore cannot pass normal CI if one of those prepared live workflows:
- loses manual dispatch;
- stops requiring `main`;
- changes a default approval from `NO`;
- changes canonical secret mapping;
- enables a committed network/forecast switch;
- removes receipt verification;
- removes the pinned sanitized artifact upload;
- adds scheduled/push/pull-request execution behavior.

This is an offline guard. It does not run any provider workflow or access credentials.
