# Phase 78 — Redacted unresolved-provider account evidence registry

Status: **ACCOUNT_EVIDENCE_HOLD / NO LIVE REQUEST**

Phase 78 adds a separate, redacted account-evidence layer for the three
providers that remain unresolved after four providers reached persisted
live-auth verification.

The registry stores only nonsecret state needed to prevent account existence,
login confirmation, product hints, or generic documentation from being
mistaken for subscription entitlement.

No email address, account ID, credential, key, token, password, or payment
information is stored.

## Provider states

### SportsDataIO

Account evidence supports:

- account exists;
- account tier is `FREE_TRIAL`;
- the provider confirmation material links to NFL documentation/data-dictionary
  resources;
- Free Trial data is explicitly scrambled and non-analytic.

The NFL link is recorded only as:

`account_product_hint = NFL`

and:

`product_hint_entitlement_proof = false`

It is not treated as proof of an NFL subscription/feed.

Current official provider pages conflict:

- the general developer/free-trial pages state Free Trial supports all
  endpoints and all 13 sports with scrambled data;
- current NFL endpoint pages still state that Free Trial only provides UEFA
  Champions League access.

The registry therefore records:

`provider_docs_scope_status = CONFLICTING`

No live request is permitted from this evidence alone.

### Sportradar

Account evidence supports only that the account registration exists.

It does not prove:

- an NFL API trial/subscription was added;
- an NFL Base package is present;
- whether the application key is `trial` or `production`;
- the rolling quota/QPS for the subscribed product.

Official Sportradar documentation states that API products are added through
the Marketplace, trials appear in the account, and access level must match the
key/product context. Until those account facts are verified, the provider
remains blocked.

### RapidAPI

Account evidence supports only that the RapidAPI account/sign-in exists.

Prior wording that the subscribed API is "all" is not treated as a specific
API product name because no product, host, plan, billing object, or endpoint
was recovered from account mail or project artifacts.

Official RapidAPI documentation requires the exact API route context,
including `X-RapidAPI-Host`, and subscription-plan quotas/billing objects are
product/plan specific.

RapidAPI therefore remains blocked until the exact subscribed API inventory
and product-to-host route are verified.

## Account evidence registry

`config/provider_account_evidence.json` is intentionally separate from
operational provider configs.

The registry records:

- verified account existence/tier facts;
- supporting product hints;
- whether hints are entitlement proof;
- provider-documentation conflict status;
- product/feed/host/access-level verification state;
- quota/overage verification state;
- whether a live request is permitted;
- whether model evidence is permitted.

Current committed state requires both:

- `live_request_permitted=false`
- `model_evidence_allowed=false`

for all three unresolved providers.

## Cross-config consistency

`provider_account_evidence_consistency.py` prevents operational provider
configs from claiming verification that the account-evidence registry does not
support.

Examples:

- SportsDataIO cannot mark trial scope reconciled while the registry still
  says the provider documentation is conflicting.
- Sportradar cannot mark product/access-level/quota verified solely because an
  account exists.
- RapidAPI cannot populate a product, host, plan, billing object, or verified
  route flags before matching account evidence exists.

This check is independent of the existing provider precondition engine so the
two layers can fail independently.

## CI enforcement

Protected validation now runs:

1. provider/model SAFE_HOLD;
2. prepared-probe default-deny checks;
3. unresolved-provider fail-closed preconditions;
4. account-evidence registry validation; and
5. account-evidence ↔ operational-config consistency.

Any contradiction or overstatement fails CI.

## Next evidence required

SportsDataIO:
- account-specific selected product/feed scope or provider support resolution;
- exact safe probe endpoint;
- quota and overage policy.

Sportradar:
- subscribed NFL product/package;
- trial vs production access level;
- quota/QPS;
- matching League Hierarchy route.

RapidAPI:
- subscribed API inventory;
- exact API product;
- exact `X-RapidAPI-Host`;
- plan/pricing type;
- billing object;
- quota and overage behavior;
- exact endpoint.

No provider request is authorized or performed by Phase 78.
