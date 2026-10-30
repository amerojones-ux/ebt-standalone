# EBT.ai API credential verification runbook — October 2026

## Step 1 — repository secret presence only
The seven secrets must exist in the GitHub Actions repository settings:
- EBT_THERUNDOWN_API_KEY
- EBT_SPORTSDATA_API_KEY
- EBT_THEODDS_API_KEY
- EBT_APISPORTS_API_KEY
- EBT_RAPIDAPI_API_KEY
- EBT_WEATHER_API_KEY
- EBT_SPORTRADAR_API_KEY

The `.github/workflows/api-secret-presence.yml` workflow uses only GitHub Actions boolean expressions to check that each secret is nonempty. It never injects actual secret values into a shell process, never prints them and never contacts an API. It is restricted to explicit manual dispatch after code review; it does not run on pushes or pull requests, reducing the risk of unreviewed workflow changes accessing secrets. A successful run establishes **presence only**, not key validity or permissions.

Do not paste keys into issue comments, logs, terminal commands, client-side code or commits.

## Step 2 — authenticated connection tests (not yet activated)
Require a separately approved backend with outbound TLS and host-level egress controls. Provider-specific API hosts and read-only endpoints must be copied from the provider's official documentation and independently reviewed. No arbitrary user-provided URL may be accepted. Select a documented header-auth endpoint; providers requiring query-string keys must use a separately reviewed adapter that redacts and prevents logs or redirects.

Provider-by-provider matrix:
| Provider | Credential | Endpoint and auth | Subscription coverage | Legal rights | Verification |
|---|---|---|---|---|---|
| TheRundown | Presence workflow previously reported successful; per-provider results not independently inspected | Not reviewed | Unknown | Unknown | HOLD |
| SportsDataIO | Presence workflow previously reported successful; per-provider results not independently inspected | Not reviewed | Unknown | Unknown | HOLD |
| The Odds API | Presence workflow previously reported successful; per-provider results not independently inspected | Not reviewed | Unknown | Unknown | HOLD |
| API-Sports | Presence workflow previously reported successful; per-provider results not independently inspected | Not reviewed | Unknown | Unknown | HOLD |
| RapidAPI | Presence workflow previously reported successful; per-provider results not independently inspected | API host varies by subscribed API | Unknown | Unknown | HOLD |
| Weather provider | Presence workflow previously reported successful; per-provider results not independently inspected | Vendor not identified | Unknown | Unknown | HOLD |
| Sportradar | Presence workflow previously reported successful; per-provider results not independently inspected | Not reviewed | Unknown | Unknown | HOLD |

`extensions/provider_probe.py` is a *header-auth-only* transport skeleton; it is not yet wired to any actual provider. An HTTP 200 JSON response is marked REACHABLE_ONLY, never licensed, fully verified or forecast-ready. Never infer production readiness from the result.

## Step 3 — model activation (HOLD)
Before model activation require verified official identity mapping, permitted historical coverage, immutable as-of snapshots, independent opponent-adjusted projections, V7.1 three-engine simulations and calibrated out-of-time performance. Betting lines must not contaminate independent projections. No production or wager activation from this workflow.

## GitHub execution note
GitHub may restrict newly added workflow files and manual dispatch to the default branch. Do not merge the draft PR solely to make manual dispatch available. Review the draft PR first. Once the workflow is safely present on the default branch, use its manual Run workflow action; if unavailable, investigate repository Actions settings and workflow permissions. Do not run secret-bearing workflows from untrusted branches. Do not claim a passing check without a completed successful run.


## Step 2A — provider onboarding evidence (mandatory before any live probe)
Maintain a reviewed, versioned record for each provider with:
1. Official vendor and product name, account/subscription tier, documented API base hostname, and exact read-only path.
2. Documented credential transport (header name or other scheme), accepted methods, expected content type, quota, and whether a billable request is incurred.
3. Permitted sports/leagues, injury/stat/history endpoints, retention and derived-model rights, and redistribution restrictions.
4. Reviewer approval of endpoint and hostname, TLS validation, network egress allowlist, and a bounded, rate-limited execution environment.
5. Sanitized results: only provider ID, connection category, observation timestamp, and gate decision; never URL, response body, key, request headers or account identifiers.

Do not configure live endpoints from guesses, search snippets, or an unreviewed branch. In particular, RapidAPI requires the subscribed upstream API product and host; the weather key requires the actual weather vendor. An unsupported query-string credential scheme must stay HOLD until a separate security-reviewed adapter exists.

## Step 2B — promotion and rollback controls
- Run credentialed probes only from a separately reviewed and protected workflow/environment; never in pull_request jobs or untrusted forks.
- Keep network egress restricted at infrastructure level; the Python hostname check alone does not prevent DNS or proxy redirection.
- Treat HTTP 200 JSON as REACHABLE_ONLY; require explicit entitlement, legal, coverage, identity and freshness verification independently.
- Record immutable as-of test evidence and revoke access immediately if unexpected outbound destinations, leaked tokens or provider policy violations are detected.
- Preserve FORECAST HOLD and WAGER NOT APPROVED until the independent model certification gate is satisfied.

## Verified offline CI checkpoint
At commit `acdf43fe7fe9d60382a2c6c73dd52e793d7dd8b3`, provider gateway run #57 and sports validation run #149 both completed successfully. These offline checks do **not** verify any live provider credential or entitlement.
