# Captured evidence ingestion, schema 1.0

This offline layer validates capture integrity and metadata. It does not authenticate a website, verify an extracted value against the page, fetch live data, establish model calibration or approve forecasts. Successful inputs remain `RESEARCH_INPUT`; rejected/missing/conflicting inputs remain `HOLD`, and an eligible official OUT report produces `REJECT` for participation. `source_truth_verified` and `forecast_approved` always remain false.

## Invocation

```sh
python3 ebt_cli.py evidence records.json \
  --requirements requirements.json \
  --raw-root local_data/raw \
  --cutoff 2026-10-28T18:01:00Z \
  --max-age-seconds 180
```

The example timestamp and freshness duration illustrate syntax. The caller must predeclare a suitable freshness policy; no universal three-minute standard is implied. Use `--policy PATH` to supply a reviewed source registry. Default `config/source_policy.json` scopes known official league domains, TeamRankings and selected secondary sources by competition. Unsupported competitions, team-specific official domains and market operators require explicit policy additions; an absent adapter/domain is not evidence of coverage.

## Record fields

Each record requires `schema_version: "1.0"`, nonempty `record_id`, `source_id`, and these exact field-key components:

| Field | Meaning |
|---|---|
| competition | Policy registry key such as NBA |
| event_id | Canonical official event identifier |
| subject_kind | event, team or player |
| subject_id | Canonical event/team/player identifier |
| fact | schedule, roster, participation, lineup, team_stat, player_stat or market |
| metric | Exact property being measured, e.g. opponent_3pa |
| window | Explicit scope such as CURRENT or 2026_27_SEASON_TO_DATE |
| snapshot_kind | LIVE or HISTORICAL |

Additional required fields: `source_kind` (official/teamrankings/secondary/market), HTTPS `source_url`, timezone-aware `effective_at` and `retrieved_at`, `value`, relative `raw_path`, and `raw_sha256`. Optional `published_at` cannot be later than retrieval. Credentials embedded in source URLs are rejected. Local captures must resolve within the specified raw root and match their SHA-256. Identical unchanged captures are hashed once per batch. Files changed while hashing are rejected.

Numeric team/player statistics also require `unit`, positive integer `sample_size`, and timezone-aware `window_start`/`window_end`. Windows must end no later than the source effective time. Numeric values preserve decimal precision and are emitted as strings. Units and sample/window metadata must agree before sources can be compared; per-game and per-possession statistics are never silently combined. Live freshness uses effective time, not the time an old page was reread. Historical statistics are exempt from live age checks but must meet the cutoff/window rules. Historical identity/availability cannot clear a live field.

Participation values: ACTIVE, OUT, QUESTIONABLE, DOUBTFUL, PROBABLE or UNKNOWN. Only ACTIVE can become a research input; activation by itself does not establish expected role/workload. Schedule, roster, lineup and market values are nonempty categorical strings in this first schema. Dedicated rich-payload adapters remain pending; do not encode incomplete identities as final proof.

## Coverage and reconciliation

`requirements.json` is a nonempty array of objects containing the eight field-key fields. Every required field gets an explicit verdict. No full-slate or worldwide completeness is inferred. Duplicate requirements are errors. Duplicate record IDs or rejected evidence associated with a field hold that field for review.

Within each source kind/domain/ID, the latest effective snapshot supersedes older snapshots; all valid records remain in the returned evidence register. Same-time contradictory records remain conflicts. Participation/schedule/roster/lineup require official authority; player statistics prefer official data; team statistics prefer TeamRankings. Secondary data alone does not clear those defaults. Conflicting latest sources hold the field even when a preferred source can be selected for review. Any latest eligible official OUT report rejects participation. Contradictory official sources require review; do not automatically clear a player because one source looks favorable.

This is intentionally conservative: source-independent supersession, numerical rounding tolerances and trusted extraction binding are not implemented. Review and version any extension rather than choosing a favorable value. There is no automatic connection from these metadata verdicts to `qualify()` evidence flags.

## Data handling

Keep raw captures and private manifests outside the public repository (`local_data/` is ignored). The CLI prints a report and does not change the raw files or write an audit entry automatically. Append reviewed results using the versioned audit layer, preserving original decisions. Tests use `.example` domains and labeled synthetic capture text, not fabricated real-player facts. No network calls, credentials, production changes, messages or wagers are part of ingestion.
