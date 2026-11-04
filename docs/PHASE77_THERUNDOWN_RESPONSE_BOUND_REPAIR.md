# Phase 77 — TheRundown response-bound repair

Status: **REPAIR INSTALLED / NO RETRY AUTHORIZED**

The first authorized TheRundown fixed-sample probe ran as GitHub Actions run
`41757989723` against protected main commit
`dd37c204b8673d0a34ada2ffffe5f3fc1e266d4c`.

The one authorized provider request was consumed.

## Observed result

The request reached the exact configured endpoint and returned far enough for
the probe to attempt bounded body acquisition. The workflow then returned:

- `THERUNDOWN_LIVE_PROBE: HOLD`
- `CATEGORY: response_too_large`

The original maximum body size was 524,288 bytes (512 KiB).

The workflow did not log or persist the oversized response body, headers, API
key, usage balance, or account fields.

The signed evidence chain still completed and produced all six artifacts:

1. execution intent;
2. execution-intent attestation bundle;
3. execution-intent verification marker;
4. sanitized HOLD receipt;
5. receipt attestation bundle; and
6. receipt attestation verification marker.

Execution-intent attestation: `63389508`

Receipt attestation: `63389545`

The HOLD receipt is preserved as historical runtime evidence and is not
rewritten or promoted.

## Repair

The canonical TheRundown request plan now uses a bounded maximum response size
of 8 MiB.

The probe additionally:

- checks a declared `Content-Length` when present;
- refuses to read a body whose declared size exceeds the cap;
- still reads no more than `MAX_BODY + 1` bytes when size is not declared;
- returns `response_too_large` for any body above the cap;
- emits only a sanitized integer byte count in the HOLD detail field; and
- continues to forbid redirects, retries, proxies, query-string credentials,
  and extra requests.

The 8 MiB limit is not a claim about the provider's guaranteed payload size. It
is a conservative bounded-memory allowance intended to accommodate the
provider's documented fixed complete-game sample while preserving fail-closed
behavior.

## Regression coverage

Tests require:

- valid JSON larger than the old 512 KiB limit to pass;
- a declared response over 8 MiB to HOLD before body read;
- an undeclared response over 8 MiB to HOLD after a bounded read;
- the request plan to remain exactly one request, no retry, no redirect; and
- the TheRundown key to remain header-only.

## Authorization boundary

Phase 77 does not authorize or perform another TheRundown request.

A new provider request requires a fresh pair of exact authorization phrases and
a new `workflow_dispatch` run. The failed/HOLD run must not be re-run because
the live-probe workflow requires `github.run_attempt == 1`.

Global provider/model state remains `SAFE_HOLD`; forecast activation and
network autorun remain disabled.
