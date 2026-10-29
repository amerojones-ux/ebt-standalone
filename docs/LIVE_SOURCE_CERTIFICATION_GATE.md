# Live Source Access and Independent Certification Gate

Status: **HOLD**. This is an implementation acceptance plan, not approval to collect restricted data or issue forecasts.

## Source policy

1. **Primary team analytics:** TeamRankings, subject to written/posted terms and robots restrictions. An HTTP 403 is a hard stop. Do not rotate IPs, forge credentials, bypass access controls, or silently substitute unapproved scrapes.
2. **Official schedule, roster and participation:** NBA official game and injury-report pages. Preserve the publication/effective time separately from retrieval time; reports change during the day.
3. **Licensed alternative:** Evaluate a contract for an authorized provider such as Sportradar NBA API or STATS Perform; confirm redistribution, retention, historical backfill, and model-training rights before implementation.
4. NBA.com/stats states statistics are not available for download for personal or academic use. Viewing public pages does not by itself establish automated collection permission.
5. Never commit credentials, proprietary raw feeds, personally identifying information or provider-prohibited data into this public repository.

## Acceptance matrix

| Gate | Required evidence | Fail state |
| --- | --- | --- |
| ACCESS | Permitted endpoint/contract, authorized authentication, bounded rate and retention rules | HOLD |
| CAPTURE | Immutable capture ID, source URL/provider, HTTP status, fetched_at, effective_at, SHA-256, parser version | HOLD |
| EXTRACTION | Exact expected schema, nonempty values, units, game/season scope, hash-reparse match | HOLD |
| IDENTITY | Canonical league game ID, team ID, player ID, roster-effective interval, independent cross-check | HOLD |
| AVAILABILITY | Timestamped official injury report, participation status, no stale carry-forward | HOLD |
| HISTORY | Pregame-locked features, independently certified outcomes, provenance and leakage checks | HOLD |
| CALIBRATION | Chronological out-of-sample test, predeclared cohort size, Brier/log loss, reliability and uncertainty, drift review | HOLD |
| RELEASE | Explicit documented human signoff and verified operational monitors; research score is not a wager approval | HOLD |

## Practical source-access work

- Request authorized TeamRankings data access or an export/license appropriate for model use. Log provider response without posting credentials.
- Independently verify official NBA schedule and injury-report page accessibility under permitted conditions.
- Compare licensed provider options for schedule, player game logs, team metrics, injuries, historical corrections, and identifiers.
- Create **synthetic-only** fixtures for each adapter, including 403, 429, malformed JSON, wrong game ID, stale injury report, traded player, missing minutes and conflicting status.
- Once permitted captures exist, test real-page schema under a fixed capture hash and review a human-readable provenance report.
- Do not switch LIVE_FORECASTING to enabled on the strength of synthetic tests, screen percentages, or in-sample isotonic calibration.

## Historical certification record

Each historical example must preserve `event_id`, `player_id`, `team_id`, `market_definition`, `threshold`, `feature_asof`, `scheduled_start`, `source_capture_ids`, `lineup_status_asof`, `model_version`, `prediction_created_at`, `outcome_source`, `outcome_final_at`, and an independently reviewed `certification_status`. A hash proves integrity of bytes, **not** that their claims are true.

## External references

- NBA official injury reporting: https://official.nba.com/nba-injury-report-2026-27-season/
- NBA stats FAQ: https://www.nba.com/stats/help/faq
- Sportradar NBA API overview: https://developer.sportradar.com/basketball/reference/nba-overview
