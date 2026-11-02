# Phase 41 — Checksum-bound reviewer decision and dry-run ledger preview

Status: **SAFE HOLD / OFFLINE**

Phase 41 adds one more non-mutating control between reviewer approval and the evidence ledger.

## Decision integrity

Reviewer decisions now include `decision_sha256`, calculated over the canonical decision body. Any mutation to reviewer, timestamp, decision, proposal, candidate hash, or safety flags causes verification failure.

Supported review decisions remain limited to the three providers that currently have hardened probe receipts:
- WeatherAPI
- The Odds API
- API-Sports

## Dry-run ledger preview

`provider_evidence_ledger_preview.py` accepts:
1. the current evidence ledger;
2. a checksum-valid **APPROVE** review decision;
3. trusted UTC time.

It then:
- validates the current ledger;
- refuses rejected or malformed decisions;
- refuses to overwrite an existing evidence record;
- inserts the proposed record only into an in-memory deep copy;
- validates the entire preview ledger against the claim-bound evidence policy;
- returns a `VALID_MANUAL_PATCH_PREVIEW`.

The result explicitly states:
- `ledger_write_permitted: false`
- `readiness_write_permitted: false`
- `forecast_activation_permitted: false`

The real `config/provider_evidence.json` and `config/provider_readiness.json` are never modified.

## Promotion chain after Phase 41

provider response
→ sanitized PASS receipt
→ checksum-bound REVIEW_ONLY candidate
→ explicit checksum-bound reviewer decision
→ dry-run ledger preview
→ separate manual ledger edit/review
→ readiness change with evidence
→ global activation review

No provider network, secret, quota, ledger mutation, readiness mutation, or forecast activation occurs in this phase.
