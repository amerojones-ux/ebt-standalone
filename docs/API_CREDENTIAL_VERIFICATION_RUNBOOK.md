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
| TheRundown | Secret presence pending CI | Not reviewed | Unknown | Unknown | HOLD |
| SportsDataIO | Secret presence pending CI | Not reviewed | Unknown | Unknown | HOLD |
| The Odds API | Secret presence pending CI | Not reviewed | Unknown | Unknown | HOLD |
| API-Sports | Secret presence pending CI | Not reviewed | Unknown | Unknown | HOLD |
| RapidAPI | Secret presence pending CI | API host varies by subscribed API | Unknown | Unknown | HOLD |
| Weather provider | Secret presence pending CI | Vendor not identified | Unknown | Unknown | HOLD |
| Sportradar | Secret presence pending CI | Not reviewed | Unknown | Unknown | HOLD |

`extensions/provider_probe.py` is a *header-auth-only* transport skeleton; it is not yet wired to any actual provider. An HTTP 200 JSON response is marked REACHABLE_ONLY, never licensed, fully verified or forecast-ready. Never infer production readiness from the result.

## Step 3 — model activation (HOLD)
Before model activation require verified official identity mapping, permitted historical coverage, immutable as-of snapshots, independent opponent-adjusted projections, V7.1 three-engine simulations and calibrated out-of-time performance. Betting lines must not contaminate independent projections. No production or wager activation from this workflow.

## GitHub execution note
GitHub may restrict newly added workflow files and manual dispatch to the default branch. Do not merge the draft PR solely to make manual dispatch available. Review the draft PR first. Once the workflow is safely present on the default branch, use its manual Run workflow action; if unavailable, investigate repository Actions settings and workflow permissions. Do not run secret-bearing workflows from untrusted branches. Do not claim a passing check without a completed successful run.
