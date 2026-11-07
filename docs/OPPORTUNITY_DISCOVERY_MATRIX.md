# Opportunity Discovery Matrix — V7/V7.1 research layer

This layer widens discovery without weakening Black Diamond qualification. It exists so a high-probability safety board does not hide structurally identifiable alternate thresholds, role-dislocation beneficiaries, long-price tail opportunities, first-event candidates, or postgame data conflicts.

## Required order

1. Verify event, identity, availability and role evidence.
2. Build and lock the independent sport/market distribution without sportsbook prices.
3. Evaluate mismatch, opportunity and role state.
4. Only after model lock ingest the complete available market ladder with exact book, line, price and timestamps.
5. Route expressions into separate discovery lanes.
6. Apply the existing V7 adversarial, MC, final revalidation, calibration and exact-price gates before any single can qualify.

## Discovery lanes

- **SAFE_ALT_RESEARCH** — a lower-fragility threshold reaches a predeclared market-family modeled-survival rule and retains positive central cushion. It is not calibrated approval.
- **TAIL_VALUE_RESEARCH** — modeled probability is below the safe lane but materially exceeds raw price-implied probability under a predeclared research rule. It remains HOLD until calibration, no-vig, live price and V7 gates are complete.
- **ASYMMETRIC_VALUE_RESEARCH** — first basket, first TD, early scoring and similar rare-event markets. This lane is always separate from Black Diamond survival qualification.
- **SHADOW** — researched expression that does not satisfy the predeclared discovery rule.
- **QUARANTINED** — screenshot/ticket result evidence conflicts with verified official identity, score or stat evidence and cannot enter learning inputs.

## Implemented controls

### Complete alternate-line comparison
The discover_count_market_expressions function consumes a complete independently locked count PMF and operator ladder. It enforces projection-before-market chronology, exact inclusive/strict settlement semantics, directional cushion, modeled survival, raw implied comparison and an efficiency-knee diagnostic.

It deliberately does **not** call raw implied probability no-vig probability and does not label its modeled EV diagnostic as live verified EV.

### Role and opportunity reallocation
The detect_role_reallocation function compares two pregame role/opportunity snapshots. A confirmed material OUT/INACTIVE/starter/role change returns FULL_RERUN_REQUIRED; an unresolved material change returns HOLD_FOR_CONFIRMATION.

Beneficiary opportunity values must come from the independent sport model. The module never invents replacement usage from sportsbook prices.

### Rare-event asymmetric value
The competing_risk_probabilities function provides a transparent constant-proportional competing-hazard research approximation. The evaluate_rare_event_quotes function compares those locked probabilities with exact quotes only after model lock.

A rare-event candidate may surface as asymmetric-value research but is explicitly ineligible for the Black Diamond survival lane merely because its offered price is attractive.

### Screenshot/result firewall
The reconcile_result_claim function compares screenshot/ticket claims with a verified official result. Any identity, final-score or player-stat disagreement returns QUARANTINED and blocks that claim from model-learning inputs.

## Non-negotiable HOLD rules

- No universal discovery threshold is hard-coded. Sport/market-family rules must be predeclared.
- Modeled probability from an uncalibrated PMF is not calibrated hit probability.
- Raw implied probability is not no-vig probability.
- Positive modeled price edge is not a high hit rate.
- Confirmed role changes trigger a full independent rerun instead of a mechanical player boost.
- Winning screenshots do not alter weights by themselves.
- The new CLI is offline only and makes no network calls or wagers.

## CLI

Run: python ebt_opportunity_discovery_cli.py --help

Modes: market-discovery, role-reallocation, rare-event, result-integrity.
