# Phase 29 — SportsDataIO access-classification and evidence gate

Status: **OFFLINE / NO LIVE REQUEST**

Official SportsDataIO developer documentation was reviewed on 2026-11-02.

## Authentication
SportsDataIO documents two authentication mechanisms: API key as a query parameter or the `Ocp-Apim-Subscription-Key` HTTP header. Black Diamond intentionally permits **header authentication only** so credentials are not placed in URLs.

## Why access classification is mandatory
A valid SportsDataIO key does not establish that returned data is live, real, current, or analysis-grade.

Official access modes include:
- **Free Trial** — structurally realistic but scrambled data; integration testing only.
- **Dev Key** — unlimited integration-scale access but still scrambled data.
- **Replay** — authentic historical games replayed on a live-like schedule; not current-day evidence.
- **Discovery Lab** — real data, but paid tiers are next-day delayed; the free tier provides last-season data.
- **Leagues API production** — real-time production feeds after a commercial agreement.
- **Global Sports API production** — real-time topline schedules/scores, not the deep stat/prop coverage implied by league feeds.

## Black Diamond evidence rule
No SportsDataIO source is automatically accepted as forecasting evidence.

Promotion to generic model evidence requires all of:
1. the access method is specifically **Leagues API production**;
2. account entitlement independently verified;
3. exact deep-feed scope independently verified;
4. freshness/current-day behavior independently verified.

Global Sports API production may, after the same verification gates, support **schedule/score evidence only**. Its topline coverage must not be treated as deep player/stat/prop evidence.

Free Trial and Dev Key data must never enter modeling, calibration, backtesting truth labels, or forecast certification because the provider explicitly documents them as scrambled.

Replay may be used for integration QA and, after independent identity checks, historical pipeline testing; it must not be represented as current-day live data.

Discovery Lab delayed/last-season data may support bounded historical research but not current live forecasting.

No network request, secret read, or forecast activation occurred in this phase.
