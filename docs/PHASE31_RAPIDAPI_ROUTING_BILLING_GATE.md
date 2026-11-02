# Phase 31 — RapidAPI product-routing and billing gate

Status: **OFFLINE / NO LIVE REQUEST**

Official RapidAPI documentation was reviewed on 2026-11-02.

## Authentication identity
RapidAPI Auth requires two headers on API Hub requests:
- `X-RapidAPI-Key` — identifies the RapidAPI app/context;
- `X-RapidAPI-Host` — uniquely identifies the specific API being called.

Therefore the presence of `EBT_RAPIDAPI_API_KEY` does **not** establish which sports API is subscribed or what endpoint is authorized.

A generic product label such as `all`, `sports`, `any`, or `unknown` is explicitly rejected. The exact API product and exact RapidAPI host must be reviewed.

## Billing boundary
RapidAPI documents API-specific pricing types including Free, Pay Per Use, Freemium and Paid. Depending on the API/plan, requests may have daily/monthly quotas and overage charges. Billing objects may also be something other than generic requests.

Before code for a live probe can even be prepared, Black Diamond requires:
1. exact API product;
2. exact `X-RapidAPI-Host`;
3. exact subscription/plan;
4. pricing type;
5. billing object;
6. current quota reviewed;
7. overage behavior reviewed;
8. exact endpoint reviewed.

Even after all eight are supplied, this phase only allows **preparation** of a provider-specific probe. It never authorizes execution.

## Forecast evidence boundary
RapidAPI is an aggregator. Data quality, identity, freshness, licensing, endpoint semantics and suitability for modeling must be assessed for the underlying API provider, not inferred from RapidAPI authentication success.

No API key read, network request, subscription change, or paid operation occurred in this phase.
