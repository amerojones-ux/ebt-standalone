# Phase 80 — Signed provider account-metadata claim workflows

Status: **CLAIM_CAPTURE_ONLY / NO PROVIDER REQUEST / NO CONFIG WRITE**

Phase 80 adds three manual GitHub workflows for capturing nonsecret account
metadata claims for the providers that remain blocked after four providers
reached persisted live-auth verification:

- SportsDataIO
- Sportradar
- RapidAPI

These workflows do not contact the providers. They do not read provider
credentials, repository secrets, account passwords, or payment information.

## Critical evidence distinction

A GitHub attestation proves:

- which GitHub actor submitted a claim;
- the exact repository and protected-main commit used;
- the exact workflow run and first-attempt provenance;
- the exact transition proposal generated from the submitted metadata; and
- that the resulting claim file has not changed since attestation.

A GitHub attestation does **not** prove that the provider portal/support page
itself was accurate or that the submitter copied it correctly.

Every claim therefore contains:

`claim_verified_against_provider_source=false`

The signed package is an **attested claim**, not entitlement evidence and not a
provider-readiness promotion.

## Workflow safety

Every workflow requires:

- manual `workflow_dispatch`;
- first run attempt only;
- protected `main`;
- immutable `github.sha` checkout;
- no checkout credentials persisted;
- no repository write permission;
- no Actions write permission;
- no provider secret access;
- no provider network request;
- no config write; and
- provider-specific confirmation phrases.

Pinned actions are used for checkout, attestation and artifact upload.

## Source types

Only two source classes are accepted:

- `ACCOUNT_PORTAL`
- `PROVIDER_SUPPORT`

A short nonsecret `source_reference` is required so a later reviewer can
associate the claim with the underlying portal snapshot or support
correspondence.

The source reference is restricted to a short safe character set and rejects
credential-like terms. Full signed URLs, query tokens, passwords, API keys,
authorization strings and secrets do not belong in this field.

## SportsDataIO claim workflow

Workflow:

`.github/workflows/sportsdataio-account-metadata-review.yml`

Inputs capture:

- source class/reference;
- exact product name;
- exact feed/scope;
- exact HTTPS v3 endpoint;
- confirmation that access tier/feed/quota/overage were reviewed; and
- explicit authorization to create a signed claim.

The claim is routed through the Phase 79 transition engine. It may propose
reconciling the current Free Trial scope conflict only when the submitter is
asserting that account-portal/provider-support evidence has actually resolved
that conflict.

It still cannot enable model evidence, forecasting or provider execution.

## Sportradar claim workflow

Workflow:

`.github/workflows/sportradar-account-metadata-review.yml`

Inputs capture:

- source class/reference;
- exact NFL product;
- exact package;
- exact `trial` or `production` access level;
- confirmation that product/access/quota were reviewed; and
- explicit authorization to create a signed claim.

The exact League Hierarchy endpoint is derived by Phase 79 from the submitted
access level; arbitrary provider endpoints are not accepted as input.

## RapidAPI claim workflow

Workflow:

`.github/workflows/rapidapi-account-metadata-review.yml`

Inputs capture:

- source class/reference;
- exact subscribed API product;
- exact `X-RapidAPI-Host`;
- pricing type;
- plan name;
- billing object;
- exact HTTPS endpoint;
- confirmation that product/host/plan/quota/overage were reviewed; and
- explicit authorization to create a signed claim.

The Phase 79 engine rejects ambiguous product names such as `all` and requires
the endpoint host to match the submitted RapidAPI host.

## Claim envelope

`provider_account_metadata_claim.py` verifies:

- exact schema;
- supported provider;
- source class;
- GitHub actor identity shape;
- repository identity;
- first-attempt run identity;
- 40-character source commit;
- valid Phase 79 transition status;
- all transition safety flags false;
- `claim_verified_against_provider_source=false`;
- all outer mutation/network/forecast flags false; and
- SHA-256 integrity of the complete claim body.

Each workflow self-verifies the claim before attestation.

## Signed package

A successful workflow:

1. creates the sanitized non-mutating transition claim;
2. self-verifies it;
3. creates a GitHub attestation;
4. independently verifies that attestation against the exact signer workflow,
   protected main ref and source digest;
5. creates a sanitized attestation marker; and
6. uploads the two-file package for seven days.

No account metadata claim is automatically written into
`config/provider_account_evidence.json`.

No operational provider config is changed.

## Required next layer

Before an attested claim can change account evidence, a separate reviewer must
bind the claim to the underlying provider-source evidence and explicitly decide
APPROVE / REJECT / HOLD.

Only an approved source-verified claim may later generate a protected PR for
the synchronized account-evidence and operational-config changes.

Even that future metadata promotion will not itself authorize a provider
network request.

Global provider/model state remains `SAFE_HOLD`.
