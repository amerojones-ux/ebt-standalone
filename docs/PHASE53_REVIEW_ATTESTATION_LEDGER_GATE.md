# Phase 53 — Signed reviewer-workflow provenance required for ledger promotion

Status: **SAFE HOLD / OFFLINE**

Phase 52 created a canonical GitHub-actor-bound review workflow and cryptographically attested its decision file. Phase 53 makes that signed review-workflow evidence mandatory for the final live-auth ledger record and every downstream promotion preview.

## Evidence ledger schema v3

`config/provider_evidence.json` is now `schema_version: 3`.

A `live_auth_verified` record must retain both evidence layers.

### Provider-side provenance

- source repository
- provider probe source commit
- receipt canonical-body SHA-256
- exact sanitized receipt-file SHA-256
- provider attestation-verification marker SHA-256
- provider attestation ID and URL
- exact provider signer workflow

### Reviewer-side provenance

- reviewer in `github:<actor>#<actor_id>` format
- review repository
- review workflow run ID
- review workflow source commit
- `review_github_metadata_match: true`
- raw review decision checksum
- exact review-decision file SHA-256
- exact review-attestation verification-marker SHA-256
- review attestation ID and URL
- exact review signer workflow:
  `.github/workflows/provider-live-auth-evidence-review.yml`

Raw/free-form review decisions cannot satisfy ledger v3.

## Strict review-package ingestion

The review workflow artifact must:

- come from `main`;
- have a valid GitHub artifact SHA-256 metadata field;
- be unexpired and within the bounded size limit;
- have the exact name:
  `provider-live-auth-review-<source-run-id>-<review-run-id>`;
- identify the same review run in artifact metadata;
- contain exactly three files:
  - `provider_review_candidate.json`
  - `provider_review_decision.json`
  - `provider_review_decision_attestation_verification.json`;
- contain no nested paths, directories, symlinks, encrypted members, or extra files.

The ingester then verifies:

1. candidate checksum/schema and provider provenance;
2. review-decision checksum/schema;
3. candidate checksum referenced by the decision;
4. source probe run ID encoded in the candidate;
5. GitHub-actor reviewer identity equality between decision and marker;
6. review marker checksum/schema;
7. review workflow run ID and source commit against external GitHub artifact metadata;
8. exact review workflow signer and authoritative repository.

Only then is an `ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW` envelope produced.

## Downstream gate changes

`provider_evidence_ledger_preview.py` now rejects raw review decisions.

`provider_live_auth_promotion_preview.py` therefore also rejects raw review decisions.

Only a checksum-valid attested review envelope can:
- produce a dry-run ledger preview;
- support the evidence-backed `live_auth_verified=true` readiness preview.

Even then, all writes remain disabled and the global provider/model state must remain `SAFE_HOLD`.

## Security boundary

The complete live-auth chain is now:

provider request
→ sanitized receipt
→ provider attestation + verification
→ GitHub artifact metadata binding
→ REVIEW_ONLY candidate
→ GitHub-actor review workflow
→ signed review decision
→ review attestation verification
→ strict review-package ingestion
→ attested review decision
→ ledger v3 preview
→ readiness promotion preview
→ still SAFE_HOLD

No provider request, credential access, ledger write, readiness write, forecast activation, or wager action occurs in this phase.


## Phase 54 operational handoff

Phase 54 adds a manual/default-NO GitHub Actions workflow that retrieves one exact signed review package, ingests its attested review decision, generates the evidence-backed live-auth promotion preview, enforces `SAFE_HOLD`, and signs/verifies the preview artifact. It does not apply the preview.
