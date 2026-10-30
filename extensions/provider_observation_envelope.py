"""Fail-closed offline schema for immutable research observation envelopes.

This validates structure only. It does not verify upstream authenticity, licensing,
or source payloads and cannot authorize forecasts or wagers.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from collections.abc import Mapping

from extensions.provider_gateway import PROVIDERS

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_REQUIRED = ("provider", "league_id", "event_id", "team_id", "player_id",
             "source_as_of_utc", "captured_at_utc", "source_record_id", "status")
_ALLOWED = frozenset(_REQUIRED)

def _time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp timezone required")
    return result.astimezone(timezone.utc)

def validate_research_envelope(record: Mapping[str, object], *, as_of_utc: str,
                               max_age_seconds: int = 3600) -> dict[str, object]:
    if not isinstance(record, Mapping):
        raise ValueError("observation must be a mapping")
    if set(record) != _ALLOWED:
        raise ValueError("missing or unexpected observation fields")
    if record["provider"] not in PROVIDERS or record["status"] != "FOUND":
        raise ValueError("provider/status not supported")
    for name in ("league_id", "event_id", "team_id", "player_id", "source_record_id"):
        value = record[name]
        if not isinstance(value, str) or not _ID.fullmatch(value):
            raise ValueError("invalid canonical or source identity")
    if type(max_age_seconds) is not int or not 0 <= max_age_seconds <= 86400:
        raise ValueError("invalid max age")
    source_time = _time(record["source_as_of_utc"])
    capture_time = _time(record["captured_at_utc"])
    now = _time(as_of_utc)
    if not source_time <= capture_time <= now:
        raise ValueError("future or inconsistent evidence chronology")
    if (now - source_time).total_seconds() > max_age_seconds:
        raise ValueError("stale observation")
    normalized = {k: record[k] for k in sorted(_ALLOWED)}
    fingerprint = sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"fingerprint": fingerprint, "status": "STRUCTURE_VALIDATED_ONLY",
            "provider": record["provider"], "source_authenticated": False,
            "rights_verified": False, "ingestion": "BLOCKED",
            "forecast": "HOLD", "wager": "NOT APPROVED"}
