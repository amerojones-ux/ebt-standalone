# Phase 30 — Sportradar NFL v7 authentication and quota contract

Status: **OFFLINE / NO LIVE REQUEST**

Official Sportradar NFL documentation was reviewed on 2026-11-02.

## Authentication and endpoint shape
Sportradar documents NFL v7 authentication with the `x-api-key` HTTP header. The current NFL base shape is:

`https://api.sportradar.com/nfl/official/{access_level}/v7/{language_code}/{feed}.{format}`

The access level is explicitly either `trial` or `production` and must match the key. The repository therefore defaults this field to `UNKNOWN` and refuses to infer it from key presence.

## Future first endpoint candidate
The low-frequency metadata candidate is League Hierarchy:

`GET https://api.sportradar.com/nfl/official/{access_level}/v7/en/league/hierarchy.json`

Official docs describe a 4-hour cache TTL and recommend pulling it daily or less. It returns league/conference/division/team identity and is useful for ID reconciliation.

## Quota boundary
Sportradar states that every API key/product has a rolling 30-day request quota and a query-per-second limit visible in the account. No official zero-quota authentication endpoint was identified.

Therefore **no live request is authorized in this phase**. Before a one-shot probe can be created, the account-specific NFL product, access level, remaining quota, and approval to consume exactly one request must be independently confirmed.

## Response contract
The offline hierarchy validator checks only identity structure needed for integration:
- league alias must be NFL;
- league/team IDs must be GUIDs;
- conferences/divisions/teams must be nested correctly;
- team IDs must be unique;
- the NFL hierarchy must contain exactly 32 teams.

Venue addresses, ownership, personnel names, and other unnecessary fields are not required for this authentication gate.

## Forecast evidence boundary
A successful future hierarchy request would establish only credential/product access and identity mapping. It would not establish live-game data entitlement, injury-feed entitlement, player-prop coverage, forecast accuracy, calibration, or production readiness.

No network request, API-key read, or quota consumption occurred in this phase.
