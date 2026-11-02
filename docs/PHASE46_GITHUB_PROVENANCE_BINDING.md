# Phase 46 — External GitHub run/commit metadata binding

Status: **OFFLINE / NO AUTOMATIC PROMOTION**

Phase 45 verifies the downloaded artifact ZIP and the sanitized receipt file, but an internally consistent receipt can still carry self-declared GitHub run/commit fields. Phase 46 requires those fields to match values supplied separately from trusted GitHub workflow/artifact metadata before a REVIEW_ONLY candidate can be created.

## Required external binding

Both review-candidate ingestion paths now require:

- `expected_run_id`
- `expected_commit`

The provider receipt must match both exactly:
- `github_run_id == expected_run_id`
- `git_commit == expected_commit`

A mismatch fails closed.

The resulting candidate includes:

`github_metadata_match: true`

This means only that the receipt fields matched the separately supplied expected values. It is **not** a cryptographic GitHub attestation by itself.

## Trusted-value source

Operationally, the expected values must come from GitHub workflow/artifact metadata retrieved independently of the receipt payload. For the connected workflow:

1. identify the manual workflow run;
2. list that run's artifacts;
3. confirm the artifact name/provider and workflow run identity;
4. obtain the run ID and associated head commit from GitHub metadata;
5. download the ZIP;
6. pass those external values into the artifact ingester.

The receipt must never be used as the source of its own expected run ID or commit.

## Checksum model

The REVIEW_ONLY candidate now binds all of:
- provider;
- source commit;
- GitHub run reference;
- external-metadata match flag;
- internal receipt checksum;
- sanitized receipt-file SHA-256;
- safety flags.

Reviewer decisions reject candidates without `github_metadata_match: true`.

## Boundary

The CLI can compare supplied metadata but cannot prove that a human caller obtained those values from GitHub. Independent provenance comes from the actual GitHub connector/API lookup used before ingestion.

No network request, provider secret, ledger mutation, readiness mutation, or forecast activation occurs in this phase.


## Phase 47 preferred implementation

The preferred path now uses `provider_github_artifact_metadata.build_trusted_binding()` with the GitHub Actions artifact metadata object. This removes the need for an operator to manually invent the expected run ID or head commit. The lower-level CLI flags remain useful for controlled testing, but production review should derive them from the independently retrieved GitHub artifact metadata.
