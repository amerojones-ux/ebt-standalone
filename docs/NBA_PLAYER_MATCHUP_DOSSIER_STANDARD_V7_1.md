# EBT.ai Black Diamond NBA — Player Matchup Dossier Standard V7.1

Effective: 2026-11-06 (America/Chicago)
Authority: user-authorized extension to the NBA Game-State Prop Discovery Standard V7.1.
Scope: NBA player-prop research only. This is a process/evidence lock, not a fitted model-weight change and not a guarantee.

## Core principle
Before a player can become a prop candidate, build a player-specific matchup dossier. The game remains the simulation unit, but every rotation player's distribution must be informed by a structured dossier rather than season averages alone.

## Required dossier for every market-relevant rotation player
1. Identity and availability: verified roster, official status, starting/closing role, restrictions, expected minutes, blowout survival.
2. Current role/opportunity: season/recent minutes, usage, touches/time of possession when verified, FGA/2PA/3PA/FTA, drives/paint touches, potential assists/passes, rebound chances and OREB/DREB split, stocks opportunities, turnovers/fouls.
3. Recent performance: exact L5/L10 game logs with role/minutes changes and outlier detection.
4. Direct opponent history: same-season H2H first, then prior-season/career H2H; minutes, PTS/REB/AST/3PM/STL/BLK, volume and efficiency.
5. Opponent environment: pace, ORtg/DRtg, shot profile, rim/paint/3PA allowance, turnovers, rebounds, assists and role/position environment.
6. Matchup mechanics: likely primary defenders, size/length, switch/drop/blitz/zone, rim protection, closeouts, PnR and transition defense.
7. Teammate competition/beneficiary graph: shared shots/rebounds/assists/closing minutes and on/off role changes caused by absences.
8. Game-script sensitivity: close game, pace changes, foul trouble, mild/large blowout.
9. Market-by-market expression: independently rank PTS/REB/AST/3PM/STL/BLK/TO/combo stability before sportsbook comparison.
10. Kill switch: strongest reason the projection can fail; material unresolved issue => HOLD.

## Evidence hierarchy / anti-overfit
A. Current official availability/role/minutes and current-season opportunity.
B. Current-season recent form and opponent environment.
C. Same-season H2H under materially similar lineup/scheme.
D. Prior-season/career H2H as contextual evidence only.
E. Analyst/narrative commentary as corroboration only.

Shrink historical H2H toward current role whenever roster, coach, scheme, minutes or usage differ. Small historical samples never override current opportunity.

## Qualification gates
No player enters the final candidate board unless identity/availability, minutes/role, current season, recent form and opponent environment are populated; H2H is checked when available; a kill switch is documented; and input/market timestamps are retained.

## Dossier-to-Monte-Carlo handoff
Use the dossier to set minutes distributions, shot/assist/rebound opportunity means and variances, efficiency priors, foul/blowout downside and teammate/opponent correlations. Then run MC-1 baseline, MC-2 adversarial and MC-3 scenario/correlation. Late news invalidates affected dossiers and triggers a rerun.

## Cross-player elimination
Build dossiers for both teams, rank PTS/REB/AST/3PM/STL/BLK leaders, detect shared-volume conflicts, prefer one player per statistical lane when possible, redirect or PASS the weaker shared-volume candidate, and avoid same-player stacking unless independent mechanisms and correlation are explicitly modeled.

## Canonical shorthand
"Run the Black Diamond NBA full game-state projection workflow" includes this player matchup dossier for every market-relevant rotation player before final Monte Carlo qualification and market selection.
