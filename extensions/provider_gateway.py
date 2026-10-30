"""Research-only secure provider configuration and fail-closed provenance checks.

No HTTP requests, secret logging, live forecast certification, or wagering.
A configured environment variable is NOT evidence of API access or licensed use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import re
from typing import Mapping

PROVIDERS = {
    "therundown": "EBT_THERUNDOWN_API_KEY",
    "sportsdata": "EBT_SPORTSDATA_API_KEY",
    "theoddsapi": "EBT_THEODDS_API_KEY",
    "apisports": "EBT_APISPORTS_API_KEY",
    "rapidapi": "EBT_RAPIDAPI_API_KEY",
    "weather": "EBT_WEATHER_API_KEY",
    "sportradar": "EBT_SPORTRADAR_API_KEY",
}
# Roles are suggestions, not proof of entitlements or endpoint coverage.
ROLES = {
    "therundown": "market_quotes",
    "sportsdata": "statistical_crosscheck",
    "theoddsapi": "market_quotes",
    "apisports": "league_coverage",
    "rapidapi": "provider_gateway",
    "weather": "environmental_context",
    "sportradar": "historical_live_statistics",
}
RIGHTS_REQUIRED = frozenset({
    "model_use", "historical_access", "retention", "derived_analytics"
})
VALID_STATUS = frozenset({"FOUND", "N_A", "BLOCKED", "STALE", "CONFLICTING"})
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class ProviderGateError(ValueError):
    """Fail-closed provider evidence or identity failure."""


@dataclass(frozen=True)
class ProviderReadiness:
    provider: str
    credential_present: bool
    rights_verified: bool
    feed_verified: bool
    status: str
    reason: str


def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ProviderGateError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderGateError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProviderGateError("timezone required")
    return parsed.astimezone(timezone.utc)


def credential_presence(environ: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Return booleans only. Never reveal, persist or hash credentials."""
    env = os.environ if environ is None else environ
    if not isinstance(env, Mapping):
        raise ProviderGateError("invalid credential environment")
    return {name: isinstance(env.get(variable), str) and bool(env.get(variable).strip())
            for name, variable in PROVIDERS.items()}


def assess_provider(provider: str, *, rights: Mapping[str, bool] | None = None,
                    feed_verified: bool = False,
                    environ: Mapping[str, str] | None = None) -> ProviderReadiness:
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ProviderGateError("unknown provider")
    present = credential_presence(environ)[provider]
    rights_ok = (isinstance(rights, Mapping) and
                 all(rights.get(k) is True for k in RIGHTS_REQUIRED))
    # Rights assertions must come from independently reviewed agreements.
    # Caller-provided booleans cannot establish independently authenticated
    # feed status or legal rights. Never unlock ingestion from this function.
    reason = "HOLD: independent rights and feed verification not implemented"
    return ProviderReadiness(provider, present, bool(rights_ok),
                             feed_verified is True, "BLOCKED", reason)


def validate_observation(record: Mapping[str, object], *,
                         as_of_utc: str, max_age_seconds: int = 3600) -> dict:
    """Validate one externally retrieved observation; never retrieve data here.

    Requires upstream adapter to supply canonical IDs and source status.
    This does not independently authenticate the upstream provider or rights.
    """
    if not isinstance(record, Mapping):
        raise ProviderGateError("observation must be a mapping")
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or max_age_seconds < 0:
        raise ProviderGateError("invalid maximum age")
    provider = record.get("provider")
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ProviderGateError("unknown provider")
    if not isinstance(record.get("status"), str) or record.get("status") != "FOUND":
        raise ProviderGateError("source not FOUND")
    for key in ("league_id", "event_id", "team_id", "player_id"):
        value = record.get(key)
        if not isinstance(value, str) or not _ID.fullmatch(value):
            raise ProviderGateError("missing or malformed canonical identity: " + key)
    observed = _utc(record.get("source_as_of_utc"))
    now = _utc(as_of_utc)
    age = (now - observed).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise ProviderGateError("future or stale source timestamp")
    # No raw payload, tokens, URL query parameters, or personal data in digest.
    canonical = {key: record[key] for key in
                 ("provider", "league_id", "event_id", "team_id", "player_id",
                  "status", "source_as_of_utc")}
    digest = sha256(json.dumps(canonical, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"status": "RESEARCH_ONLY", "forecast": "HOLD",
            "wager": "NOT APPROVED", "source_fingerprint": digest,
            "provider": provider, "event_id": record["event_id"]}


def inventory(environ: Mapping[str, str] | None = None) -> dict:
    """Safe diagnostic: no network, no credential values, no approval claims."""
    present = credential_presence(environ)
    return {"mode": "OFFLINE", "forecast": "HOLD", "wager": "NOT APPROVED",
            "providers": [{"name": p, "role": ROLES[p],
                           "credential_present": present[p],
                           "feed_verified": False, "rights_verified": False,
                           "status": "BLOCKED"} for p in PROVIDERS]}
