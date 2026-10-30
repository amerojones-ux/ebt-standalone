"""Research-only player-prop market normalization with strict source separation.

Input is an already retrieved vendor record. This module makes no network calls,
asserts no provider rights, and does not derive probabilities from market prices.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

_ALLOWED_MARKETS = frozenset({
    "points", "rebounds", "assists", "three_pointers", "pra",
    "passing_yards", "rushing_yards", "receiving_yards", "receptions",
    "strikeouts", "hits", "total_bases", "saves", "shots_on_goal",
})
_ALLOWED_SIDES = frozenset({"over", "under"})
_MARKET_PROVIDERS = frozenset({"therundown", "theoddsapi"})


def _time(s):
    if type(s) is not str:
        raise ValueError("timestamp required")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid timestamp") from None
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("timezone required")
    return d.astimezone(timezone.utc)


def normalize_prop_quote(record: Mapping[str, object], *, as_of_utc: str,
                         max_age_seconds: int = 300) -> dict[str, object]:
    """Validate normalized vendor fields and return research-only market data."""
    if not isinstance(record, Mapping):
        raise ValueError("invalid record")
    if type(max_age_seconds) is not int or not 0 <= max_age_seconds <= 3600:
        raise ValueError("invalid age limit")
    provider = record.get("provider")
    if provider not in _MARKET_PROVIDERS:
        raise ValueError("provider not approved for market comparison")
    market = record.get("market")
    side = record.get("side")
    if market not in _ALLOWED_MARKETS or side not in _ALLOWED_SIDES:
        raise ValueError("unsupported prop category or side")
    for field in ("league_id", "event_id", "player_id", "bookmaker_id"):
        val = record.get(field)
        if type(val) is not str or not val.isascii() or not 1 <= len(val) <= 128 or not all(
                c.isalnum() or c in "_.:-" for c in val):
            raise ValueError("missing canonical identifier")
    line = record.get("line")
    if type(line) not in (int, float, str, Decimal):
        raise ValueError("invalid line")
    try:
        numeric = Decimal(str(line))
    except InvalidOperation:
        raise ValueError("invalid line") from None
    if not numeric.is_finite() or numeric < 0 or numeric > 10000:
        raise ValueError("line out of range")
    source_time = _time(record.get("source_as_of_utc"))
    cutoff = _time(as_of_utc)
    if not 0 <= (cutoff - source_time).total_seconds() <= max_age_seconds:
        raise ValueError("stale or future market quote")
    return {
        "provider": provider,
        "league_id": record["league_id"],
        "event_id": record["event_id"],
        "player_id": record["player_id"],
        "bookmaker_id": record["bookmaker_id"],
        "market": market,
        "side": side,
        "line": str(numeric),
        "source_as_of_utc": source_time.isoformat(),
        "status": "RESEARCH_ONLY",
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
        "use": "market_comparison_only",
    }
