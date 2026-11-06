# November 5, 2026 screenshot audit — reconciliation specification

Status: EVIDENCE REVIEW; NOT MODEL-CERTIFIED. Source: three user-provided DraftKings betslip screenshots. These are proposed selections, not proof of wager placement.

## Exact screenshot selections
Orlando @ Phoenix (+467):
- Wendell Carter Jr 8+ rebounds
- Franz Wagner 6+ assists
- Desmond Bane 15+ points
- Khaman Maluach 4+ rebounds
- Miles Bridges 15+ points
- Devin Booker 4+ assists

Miami @ Golden State (+369):
- Davion Mitchell 6+ assists
- Giannis Antetokounmpo 10+ rebounds
- Davion Mitchell 10+ points
- Draymond Green 4+ assists
- Brandin Podziemski 4+ rebounds
- Stephen Curry 3+ made threes

Two-game SGP+ (+296):
- Stephen Curry 3+ made threes
- Davion Mitchell 6+ assists
- Desmond Bane 2+ made threes
- Wendell Carter Jr 10+ points
- Miles Bridges 15+ points

## Deduplication
17 displayed legs; 14 distinct (game, player, market, threshold) keys. Three repeated keys: Curry 3+ threes, Mitchell 6+ assists, Bridges 15+ points. Do not count duplicates as independent calibration observations.

## Source and audit controls
- Confirm game IDs, actual roster, final box scores and stat revisions using official NBA records.
- Maintain separately: screenshot extraction, independently verified final settlement, pregame forecast evidence.
- Preserve original pregame timestamps, projected minutes, usage, injury status, probability, scenario parameters, MC seed, version and source publication timestamps. Missing forecast => NO CERTIFICATION, not retroactive estimate.
- Distinguish exact-threshold hits from large-cushion hits; record realized margin = actual - required threshold.
- For joint probabilities model common pace, shooting, minutes, teammate competition, foul/blowout and correlated markets.
- No assumed combined payout: three displayed SGP prices overlap and cannot be multiplied to price a deduplicated parlay.
- Test historical probability calibration with out-of-time evaluation, reliability curves, Brier score, log loss and confidence intervals. Proposed 80/85/90% grades require empirical support.
- Any unresolved player/team or data-revision discrepancy => HOLD pending source reconciliation.

## Engineering acceptance criteria
1. Every displayed leg maps to one canonical immutable selection ID; repeated occurrences linked.
2. Official final stats recorded with retrieval timestamp and source URL.
3. 14 unique props independently graded with missing/void handling.
4. Original forecast evidence fetched or explicitly marked unavailable.
5. Joint MC and calibration tests reproducible and compared with adverse scenarios.
6. No production forecast status changed without separate authorization.

Official source links:
- https://www.nba.com/game/orl-vs-phx-0022600187/box-score
- https://www.nba.com/game/0022600188-heat-vs-warriors-san-francisco-ca-11-05-2026?watch=
