# Phase 22 — dual-consent WeatherAPI live-probe gate

Status: **PREPARED / NOT EXECUTED**

A live WeatherAPI request now requires two independent confirmations:

1. The account owner confirms that the WeatherAPI subscription, quota and billing implications have been reviewed.
2. The account owner separately approves exactly one live request.

Both GitHub Actions inputs default to **NO**. If either confirmation is absent, the job does not run. The Python probe also independently checks both phrases before reading the API secret.

## What this proves
A successful future run can establish only that one credential authenticated and that one current-weather payload passed the existing schema, identity and freshness checks.

## What this does not prove
- The user's actual WeatherAPI plan or billing state.
- Remaining monthly quota.
- Entitlement to other WeatherAPI endpoints.
- Sports-data correctness.
- Forecast accuracy.
- Production readiness.

No live request has been executed by this phase.
