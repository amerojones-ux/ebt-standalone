# Phase 25 — The Odds API v4 zero-quota authentication contract

Status: **OFFLINE CONTRACT / NO LIVE REQUEST**

Official v4 documentation reviewed on 2026-11-02.

## Approved future first-check candidate
- Provider: The Odds API
- Secret: `EBT_THEODDS_API_KEY`
- Method: GET
- Host: `https://api.the-odds-api.com`
- Path: `/v4/sports`
- Authentication: `apiKey` query parameter.
- Purpose: authenticate the credential and enumerate in-season sports.
- Documented quota cost: **0 usage credits** for the `/sports` endpoint.
- Required response quota headers: `x-requests-remaining`, `x-requests-used`, `x-requests-last`.
- Acceptance requires `x-requests-last == 0`; any nonzero value is HOLD.

## Data contract
The response must be a non-empty list of unique sport objects. Each accepted item requires a normalized sport key, non-empty group/title, strict boolean `active`, and strict boolean `has_outrights`.

## Black Diamond evidence rule
The Odds API is a market-data source, **not forecast validation evidence**. Sportsbook prices, lines, consensus, or bookmaker probabilities may be compared only after the independent Black Diamond model is locked. They must not increase model hit probability, projection cushion, calibration score, or certification status.

## Prohibited until separately approved
- `/odds`, player-prop or event-odds calls.
- Historical odds endpoints.
- Multi-region or multi-market calls.
- Any request with nonzero quota cost.
- Automatic polling or scheduled network execution.

Official docs state ordinary odds usage cost depends on regions and markets, while historical odds cost is materially higher. Therefore those routes remain outside this first authentication phase.

No API key was read and no network request was made.
