# EBT.ai protected provider onboarding — execution contract

**Scope:** Sports analytics only. **Status:** FORECAST HOLD / WAGER NOT APPROVED.

## What is actually verified
The seven-provider intake YAML is schema-checked in offline CI; evidence completeness and freshness are evaluated without credentials. These checks do **not** authenticate vendors, entitlements, reviewer identity, provider data, or production network controls.

## Required next steps (one provider at a time)
1. Independently identify the exact subscribed product and account entitlement using the vendor portal or contract; record only nonsecret metadata in the intake. For RapidAPI, identify each upstream API product and its required `X-RapidAPI-Host`. For weather, confirm the actual account vendor and permitted endpoints.
2. Obtain and independently review official documentation for the exact HTTPS hostname, read-only path, method, authentication transport, quotas and expected response schema. A URL from a search result alone is not approval.
3. Obtain legal review of model training/use, derived analytics, retention, historical access and redistribution rights. Store signed decisions in a protected evidence system, not as self-attested YAML booleans.
4. Establish protected runner/environment with restricted reviewer access, outbound firewall/egress allowlist, TLS verification, rate limits, no redirects, no raw response logging, and rotation/revocation plan. GitHub repository secrets alone do not provide egress isolation.
5. Run a separately authorized, read-only connection test in that environment. Only sanitized result classifications may leave the runner. HTTP 200 means reachability, not authorization or licensed coverage.
6. Verify canonical league/event/team/player identity, time provenance, as-of snapshots, source freshness, and rights before allowing **research-only** ingestion. Any uncertainty stays BLOCKED.
7. Independently certify model calibration, out-of-time backtests, correlation-aware simulations and postgame settlement before changing forecast release state. No step above independently approves wagers.

## Known implementation boundaries
- `extensions/provider_probe.py` only supports X-API-Key or Bearer headers, with explicit host and endpoint allowlists. It is not wired to a live provider.
- RapidAPI's dual-header scheme and WeatherAPI.com's query-key scheme are **not supported** by the current probe. Do not adapt by placing secrets into logged URLs or generic probe configuration.
- Provider preflight and evidence checks are offline metadata assessments. They cannot attest independent legal review or unlock live ingestion.
- All new live probe actions require explicit security review and authorization. Do not execute them in ordinary PR CI.

## Verification commands (safe, no credentials)
```bash
python -m unittest discover -s tests -p 'test_provider_*.py' -v
python -m extensions.provider_preflight docs/provider-live-verification-intake.yml
```

## Release decision
**FORECAST HOLD · WAGER NOT APPROVED · PRODUCTION DEPLOYMENT DISABLED.**
