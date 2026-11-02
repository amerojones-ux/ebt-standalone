# Phase 28 — API-Sports NFL/NCAA zero-quota status contract

Status: **OFFLINE CONTRACT / NO LIVE REQUEST**

Official API-Sports NFL & NCAA documentation was reviewed on 2026-11-02.

## Approved future first-check candidate
- Provider family: API-Sports
- Product selected for first authentication: NFL & NCAA / API-American-Football
- Secret: `EBT_APISPORTS_API_KEY`
- Method: GET
- Host: `https://v1.american-football.api-sports.io`
- Path: `/status`
- Authentication: `x-apisports-key` request header.
- Official documentation states that the `status` call does **not** count against the daily quota.

## Response headers
The documentation states that API responses include:
- `x-ratelimit-requests-limit` — daily allocation;
- `x-ratelimit-requests-remaining` — daily remaining;
- `X-RateLimit-Limit` — per-minute limit;
- `X-RateLimit-Remaining` — per-minute remaining.

The offline validator normalizes these names to lowercase, requires nonnegative integers, and rejects remaining values above their corresponding limits. Exact account quota values are sensitive operational metadata and must not be copied into a future receipt or Actions summary.

## Status payload privacy boundary
The status response may contain account, subscription, and usage information. Black Diamond must not log or persist those raw fields. The validator checks only a generic JSON envelope: a non-empty `response` object, no provider-reported error object, and an optional nonnegative integer `results`. It deliberately does not inspect, print, or serialize account names, email addresses, subscription identifiers, billing details, or exact quota balances.

## Execution policy
A future live probe must be manual-only, main-only, one request, no retry, no redirect follow-up, direct HTTPS without environment proxies, <=10 second timeout, bounded response size, secret-safe logs, sanitized PASS/HOLD categories, and an integrity-checksum receipt that contains no account data.

The public API-Sports site currently advertises a free plan and 100 requests/day for each API, but the repository must not infer the plan attached to this specific key. Account-specific entitlement remains unverified.

No API request or credential read occurred in this phase.
