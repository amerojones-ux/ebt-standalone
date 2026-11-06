# EBT.ai Black Diamond NBA — Game-State Prop Discovery Standard V7.1

Effective: 2026-11-06 (America/Chicago)
Authority: user-authorized NBA workflow clarification, compatible with the full V7 and V7.1 master. This is a process lock, not a fitted weight change and not a promise of perfect outcomes.

## Core principle
The game is the simulation unit. The mismatch is the signal. The prop is the vehicle.

Do not begin with a sportsbook prop or a player's recent hit rate. Reconstruct the expected game first, then derive every player's statistical distribution from that same game-state model. Only after all independent projections are locked may exact market thresholds and prices be compared.

## Required execution order
1. Verify complete official NBA slate, game IDs, tip times, venue and current event status.
2. Verify both rosters, transactions, official injury report, active/inactive status, projected/confirmed starters, restrictions and expected rotation.
3. Build team environment for each side: pace, ORtg, DRtg, eFG%, 2P/3P profile, rim/paint/transition, turnover creation, offensive/defensive rebound rates, free-throw generation/allowance, opponent shot profile, home/away, rest/travel and blowout sensitivity.
4. Build the rotation graph before projecting stats. For every rotation player estimate start probability/minutes distribution, substitution/closing role and blowout survival, usage/touches/time of possession, FGA/2PA/3PA/FTA, drives/paint touches/catch-and-shoot/pull-up volume, potential assists/passes, rebound chances and OREB/DREB role, steal/block event opportunities, defensive assignment/foul risk, and on/off beneficiary competition caused by absences.
5. Build matchup allocation: likely primary defenders, size/length/athleticism, switch/drop/blitz/zone tendencies, rim protection, perimeter closeouts, pick-and-roll coverage, transition defense and positional weaknesses.
6. Lock independent player opportunity distributions before market review.
7. Generate the full player forecast matrix for each team: MIN, USG, FGA, 3PA, FTA, potential AST, rebound chances, PTS, REB, AST, 3PM, STL, BLK, TO and relevant combo markets.
8. Simulate the game jointly so teammate competition, pace and correlations are preserved.
9. Compare projected player distributions and identify team leaders in PTS, REB, AST, STL, BLK and 3PM, plus runner-up and uncertainty.
10. Only after the full game model is locked, ingest exact sportsbook markets/lines/odds/timestamps and enumerate all credible market expressions.
11. Select the least-fragile expression of the projected edge. A star's points over is not preferred when rebounds, assists, threes or an alternate threshold better captures the same structural opportunity.
12. Apply V7/V7.1 qualification, price/EV, uncertainty and HOLD/PASS/REJECT rules.

## Joint Monte Carlo standard
For every game with complete critical inputs, run three purpose-distinct joint simulations. Default NBA research target is 250,000 trials per run (750,000 game-state trials total); V7 minimum remains 100,000 per run.

- MC-1 BASELINE: locked expected rotation, minutes, pace, usage, shot/rebound/assist opportunities and efficiency distributions.
- MC-2 ADVERSARIAL: reduced minutes/usage, foul trouble, lower pace, tougher defensive assignment, teammate opportunity competition, shooting regression, role compression and mild blowout effects.
- MC-3 SCENARIO/CORRELATION: close/mild/large blowout, pace-up/down, hot/cold team shooting, lineup branches for unresolved statuses, shared rebound/assist dependencies and player-player correlations.

Persist model/input version, reproducibility state, trial count, assumptions, P10/P25/P50/P75/P90, exact-threshold survival, scenario floor and dominant failure mechanism. Missing run artifacts = NOT RUN/PENDING.

## Generative market engines
- Points: minutes, usage, 2PA/3PA/FTA mix and efficiency; do not model PPG alone.
- Rebounds: opponent missed shots, on-court share, rebound chances, OREB/DREB role, capture share, lineup size and teammate competition.
- Assists: touches/time of possession, potential assists, pass opportunities, teammate conversion and role competition; do not model APG alone.
- 3PM: 3PA volume first, then make probability adjusted for shot type, coverage, opponent allowance and role.
- Steals/blocks: low-count event distributions from opponent turnover/drive/rim opportunity, defensive assignment, minutes and foul risk; stronger uncertainty treatment required.
- Combo markets: derive from the joint component simulation; never add independent marginal probabilities.

## Per-game output contract
Each matchup report must contain:
A. Game environment — projected score/range, possessions, rotation/start status, exploitation map, scripts and team-category leader forecast.
B. Team 1 full player matrix — minutes/range, role, usage/touches, FGA/3PA/FTA, potential assists, rebound chances, P50/range for PTS/REB/AST/3PM/STL/BLK, team ranks, mechanism and kill switch.
C. Team 2 full player matrix — same fields.
D. Cross-team comparison — projected top 3 in PTS/REB/AST/3PM/STL/BLK with uncertainty.
E. Market-expression board after model lock — exact current line/book/time if verified, P50/range, central/adverse cushion, MC-1/2/3 exact-line survival, main-line verdict, one preferred alternate, one replacement market, status.
F. Field-leader/manual-selection view — bold each team's best projected players in PTS, REB, AST, 3PM, STL and BLK so the user can choose the cleanest market expression rather than forcing points.

## Best-expression selection logic
1. Identify the statistical category where opportunity is most stable.
2. Compare model median to markets only after model lock.
3. Prefer the threshold that retains the structural mismatch while reducing unnecessary variance.
4. Reject a headline points prop when another market has better cushion, adverse survival and role stability.
5. Do not manufacture a candidate when no market survives.

## Daily replication rule
The November 5 winning screenshot set is outcome evidence, not a probability guarantee. Preserve the repeatable process: full game/player projections first, category leaders second, cleanest market expression third, late lineup revalidation, then immutable postgame audit. Do not change weights from one winning slate.

## Status and calibration
Black Diamond forecast qualification remains governed by V7/V7.1: calibrated probability >=87%, lower bound >=80%, positive central and adverse cushion, three simulations executed, complete evidence and no critical contradiction. Wager approval is separate and additionally requires verified current price/rules and positive EV. Modeled 80%+ survival may be shown as research but is not validated probability without calibration/lower-bound support.

## Refresh / kill switch
Rebuild the affected game when any material input changes: IN/OUT, starter change, minutes restriction, transaction, role/rotation change, material rest/travel update or verified tactical information. Refresh near T-90/T-45/T-25/T-10 where operationally supported.

## Canonical shorthand
"Run the Black Diamond NBA full game-state projection workflow" means this process plus the complete V7/V7.1 master.
