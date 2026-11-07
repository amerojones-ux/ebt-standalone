# EBT.ai Black Diamond NBA — Bench Explosion Forecast Standard V7.1

Effective: 2026-11-06 (America/Chicago)
Authority: user-authorized extension to the NBA Game-State Prop Discovery and Player Matchup Dossier standards.
Scope: NBA reserve/bench player forecasting. Process/evidence lock only; no fitted-weight change or guarantee.

## Core principle
A bench explosion is an opportunity-regime change, not a hot-hand guess. Project reserves from conditional minutes, role, possession share and event opportunities under specific lineup/game-script branches. Never promote a bench player because of one big prior box score alone.

## Bench player universe
Evaluate every non-starter expected to receive material rotation minutes, plus inactive-to-active returnees and deep reserves who become first-line beneficiaries of an absence. Default inclusion gate: expected >=8 minutes or >=10% probability of >=16 minutes, unless a role-trigger branch justifies inclusion.

## Required bench dossier
For every eligible reserve, record:
1. Verified availability, expected bench slot, start probability, closing probability and rotation position.
2. Baseline minutes distribution and minutes elasticity under each starter-out/foul/blowout branch.
3. Substitution pattern: first check-in, quarter anchors, second-unit overlap, stagger with stars, closing-lineup access.
4. Current opportunity: USG%, touches/time of possession when verified, FGA/2PA/3PA/FTA, drives, paint touches, potential assists/passes, rebound chances/OREB/DREB, steals/blocks opportunities, fouls/turnovers.
5. Per-minute and per-possession production for PTS/REB/AST/3PM/STL/BLK/TO, with shrinkage for small samples.
6. On/off beneficiary map: exact role change when each relevant starter sits; identify who inherits minutes, shots, touches, potential assists, rebound chances and defensive events.
7. L5/L10 game logs with minutes context; separate normal-bench games from elevated-role games.
8. Same-season H2H and prior H2H only after controlling for role/minutes similarity.
9. Opponent bench environment: second-unit pace, bench defense, rim/3P/rebound/turnover allowances, foul generation and transition frequency when available.
10. Matchup mechanics: likely bench defender, size/length, coverage, matchup hunting and scheme fit.
11. Game-script sensitivity: close game, mild blowout, large blowout, foul trouble, injury/early-exit and garbage-time branches.
12. Market expression ranking and kill switch.

## Bench Explosion Score (BES)
Use a transparent research score to prioritize investigation, not as a calibrated probability:
- 25% Minutes Upside: expected added minutes vs normal baseline across branches.
- 20% Role/Usage Delta: change in usage/touches/FGA/potential assists/rebound chances.
- 15% Starter-Out Beneficiary Share: share of vacated opportunity captured.
- 10% Closing/Blowout Survival: probability reserve remains on floor in favorable scripts.
- 10% Opponent Bench Matchup: second-unit weakness and positional fit.
- 10% Per-Minute Productivity Stability: role-conditioned production with shrinkage.
- 5% Recent Elevated-Role Confirmation: only games with comparable role/minutes.
- 5% Correlation/Competition Penalty: subtract for teammates competing for the same opportunity.

BES is a screening score only. It must never be presented as hit probability.

## Opportunity Explosion Index (OEI)
For each stat family compute conditional opportunity lift relative to normal reserve baseline:
- Minutes lift = scenario minutes / baseline bench minutes.
- Shot lift = scenario FGA / baseline FGA.
- Creation lift = scenario potential assists / baseline potential assists.
- Glass lift = scenario rebound chances / baseline rebound chances.
- Perimeter lift = scenario 3PA / baseline 3PA.
- Defensive-event lift = scenario steal/block opportunities / baseline.

Flag a potential explosion when at least two material opportunity dimensions rise >=25%, or one rises >=40%, with a verified mechanism.

## Bench-specific Monte Carlo
For each eligible reserve, use the joint game simulation but retain conditional branch outputs:
- NORMAL ROTATION branch.
- STARTER-OUT / ROLE-UP branch(es).
- FOUL-TROUBLE beneficiary branch.
- CLOSE-GAME closing-lineup branch.
- MILD BLOWOUT branch.
- LARGE BLOWOUT / garbage-time branch.

Persist branch probabilities only when evidence-supported; otherwise report branch-specific outcomes without assigning invented weights.

Run MC-1 baseline, MC-2 adverse and MC-3 scenario/correlation at the game level. Bench outputs must include minutes P10/P25/P50/P75/P90 and each stat distribution by branch.

## Bench market selection
Do not default to points. Rank each reserve's cleanest expression from PTS, REB, AST, 3PM, STL, BLK, TO and combos.

## Candidate gate
A reserve can enter the final Bench Explosion board only when roster/status is verified; baseline and upside minutes distributions are documented; a specific opportunity-transfer mechanism exists; current role and recent comparable-role samples are available; opponent environment and matchup mechanics are assessed; joint MC branches are retained or marked NOT RUN; a kill switch is documented; and the prop is selected only after independent projection lock.

## Classification
- TIER A — STRUCTURAL EXPLOSION: verified role-up plus strong opportunity transfer, survives adverse branch.
- TIER B — SCRIPT EXPLOSION: primarily dependent on blowout/foul/rotation scenario.
- TIER C — VOLATILE MICROWAVE: shot-driven upside with weak floor.
- HOLD — unresolved status/rotation or insufficient opportunity evidence.
- PASS — no meaningful opportunity expansion or market consumes edge.

## Anti-hindsight / calibration
Preserve every pregame bench forecast immutably. Postgame, audit minutes realization, opportunity realization, stat conversion and branch identification separately. A bench player who explodes by random shooting variance without the projected opportunity mechanism is not a model success. Do not change weights because one bench player hit.

## Canonical shorthand
"Run the Black Diamond NBA full game-state projection workflow" includes the Player Matchup Dossier Standard and this Bench Explosion Forecast Standard for every eligible reserve before final candidate selection.
