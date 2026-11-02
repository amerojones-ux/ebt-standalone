# Phase 32 — TheRundown v2 access, delay and data-point billing contract

Status: **OFFLINE / NO AUTHENTICATED REQUEST**

Official TheRundown documentation was reviewed on 2026-11-02.

## Authentication
Authenticated Product API requests use the `X-TheRundown-Key` header and the v2 base URL `https://therundown.io/api/v2`.

The provider also documents two reference endpoints that work without a key:
- `/api/v2/sports`
- `/api/v2/affiliates`

Success on those public endpoints must **never** be represented as successful API-key authentication.

## Billing model
TheRundown meters many product responses in **data points**, where one HTTP request can bill multiple returned rows. The provider documents `X-Datapoints` as authoritative for billed total on billed responses and exposes usage/remaining/limit/period headers.

Because an authenticated snapshot can consume many data points, no authenticated smoke request is authorized in this phase.

## Current plan distinctions
Official self-serve documentation currently states:
- Free: 5-minute delay, no live in-game odds, no player props/alternate markets, no WebSocket.
- Starter: 60-second delay.
- Pro: 30-second delay.
- Ultra and higher: zero-delay real-time access; WebSocket begins on Ultra.

The repository defaults the account plan to `UNKNOWN`. Presence of a key does not establish the plan or capabilities.

## Overage boundary
The provider documents different overage behavior by billing cadence and plan configuration. Monthly/annual plans are hard-capped by default unless overage is enabled; current weekly subscriptions may use metered overage. Therefore exact plan, data-point quota, and overage/spend controls must be reviewed before any authenticated call.

## Forecast evidence boundary
Sportsbook prices and markets are comparison data only and must not validate Black Diamond probabilities.

A TheRundown feed can become eligible for **live identity/freshness evidence** only if:
1. the verified plan is real-time capable;
2. the actual response explicitly reports zero data delay;
3. player/event identity is independently reconciled;
4. freshness is independently verified.

Delayed plans must never be represented as real-time current evidence.

No key was read and no authenticated request or billed data-point consumption occurred in this phase.
