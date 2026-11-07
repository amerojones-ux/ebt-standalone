# NBA Official Injury Report → Role Revalidation Layer

This layer treats the NBA's official injury report as A1 role/availability evidence while remaining fail-closed about PDF extraction, canonical identity, schedule reconciliation and freshness.

## Source contract

Official injury-report index:

- `https://official.nba.com/nba-injury-report-2026-27-season/`

Official linked PDFs are accepted only from:

- host `ak-static.cms.nba.com`
- path prefix `/referee/injury/`
- filename pattern `Injury-Report_YYYY-MM-DD_HH_MMAM|PM.pdf`

The filename timestamp is used as the report publication timestamp. A later file may never be used for an earlier forecast cutoff.

## Deliberate PDF extraction boundary

The repository is standard-library-only and does not silently add a PDF/OCR dependency. PDF bytes must therefore be transformed into the exact structured row schema by a separately reviewed extractor that preserves source URL, capture time and row provenance.

The validator accepts only:

- game date
- game-time label from the report
- matchup code
- team
- player name
- current status
- reason
- explicit submission status

The module itself does **not** claim that the upstream PDF extraction was correct; that remains a separate verification obligation.

## Status semantics

Recognized player statuses are:

- Available
- Probable
- Questionable
- Doubtful
- Out

`NOT_YET_SUBMITTED` is a team submission state, not a player status. It forces HOLD.

No absent player is inferred to be Available. No player disappearing from one report to the next is assumed healthy; removal triggers `PLAYER_REMOVED_REQUIRES_CONFIRMATION` and HOLD.

A submitted team with zero listed players is not inferred from absence. Until an extraction/source contract explicitly proves a clean submitted team, the event remains HOLD.

## Schedule and identity firewall

The injury PDF's printed game-time label is not used to construct the event start because it lacks an unambiguous AM/PM designator. Every report row must reconcile to a separate official schedule record containing:

- canonical event ID
- timezone-aware event start
- exact event key

Team and player identities are exact-map only. Fuzzy name matching is forbidden.

## Rerun behavior

Any of the following triggers a fresh independent model rerun:

- team report moves from NOT_YET_SUBMITTED to SUBMITTED
- player is newly added
- player current status changes
- player reason changes
- player is removed from the report

Removal also remains HOLD until confirmed. A rerun trigger does not itself increase or decrease a player's projection; the independent opportunity/usage model must recompute the distribution.

## Game gate

A game can clear this role-input layer only when:

- official report is available before the forecast cutoff
- report is within the predeclared freshness window
- capture is pregame
- event schedule is verified
- canonical team/player identities are verified
- both teams are explicitly represented as SUBMITTED

Clearing this layer produces research input, never wager approval.

## CLI

`nba_official_injury_cli.py` exposes:

- `index`
- `normalize`
- `bind`
- `diff`
- `gate`

It makes no network calls and performs no PDF extraction.
