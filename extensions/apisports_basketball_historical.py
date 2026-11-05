"""API-Sports Basketball historical mapping for Black Diamond research.

No network calls occur here. The mapper consumes provider payloads plus explicit
availability evidence and emits normalized records for OfficialBoxScoreSnapshotAdapter.

Important:
- API-Sports is not treated as A1 official league/team evidence.
- Only FT/AOT game states are eligible for statistical ingestion.
- Postponed/cancelled/suspended/awarded/abandoned states never become final stats.
- Missing/low minutes never imply an injury.
- Historical availability time must be supplied; it is never inferred from retrieval time.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PROVIDER_ID = "API_SPORTS_BASKETBALL"

FINAL_STATUSES = {"FT", "AOT"}
LIVE_STATUSES = {"NS", "Q1", "Q2", "Q3", "Q4", "OT", "BT", "HT"}
NONFINAL_TERMINAL_STATUSES = {"POST", "CANC", "SUSP", "AWD", "ABD"}
KNOWN_STATUSES = FINAL_STATUSES | LIVE_STATUSES | NONFINAL_TERMINAL_STATUSES

COUNT_STATS = {
    "points": ("points",),
    "rebounds": ("rebounds", "total"),
    "assists": ("assists",),
}
CONVERSION_STATS = {
    "field_goals": ("field_goals",),
    "threepoint_goals": ("threepoint_goals",),
    "freethrows_goals": ("freethrows_goals",),
}


@dataclass(frozen=True)
class EventDisposition:
    provider_status: str
    category: str
    final_stats_eligible: bool
    settlement_eligible: bool
    reason: str


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def parse_provider_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        return _aware(value, name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be an ISO-8601 string or datetime")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be valid ISO-8601") from exc
    return _aware(dt, name)


def parse_minutes(value: Any) -> Optional[float]:
    """Convert API-Sports M:SS minutes to decimal minutes; preserve missing as None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < 0:
            raise ValueError("minutes cannot be negative")
        return float(value)
    if not isinstance(value, str) or ":" not in value:
        raise ValueError("minutes must be M:SS, numeric, or null")
    minute_text, second_text = value.split(":", 1)
    if not minute_text.isdigit() or not second_text.isdigit():
        raise ValueError("minutes must be M:SS")
    minutes, seconds = int(minute_text), int(second_text)
    if seconds >= 60:
        raise ValueError("seconds must be <60")
    return minutes + seconds / 60.0


def classify_game_status(short_status: Any) -> EventDisposition:
    if not isinstance(short_status, str) or not short_status:
        return EventDisposition("", "UNKNOWN", False, False, "missing provider status")
    status = short_status.upper()
    if status in FINAL_STATUSES:
        return EventDisposition(status, "FINAL", True, True, "finished game")
    if status in LIVE_STATUSES:
        return EventDisposition(status, "LIVE_OR_NOT_STARTED", False, False,
                                "event is not final")
    if status == "POST":
        return EventDisposition(status, "POSTPONED", False, False,
                                "postponed event requires new event-time reconciliation")
    if status == "CANC":
        return EventDisposition(status, "CANCELLED", False, False,
                                "cancelled event has no final statistical settlement")
    if status == "SUSP":
        return EventDisposition(status, "SUSPENDED", False, False,
                                "suspended event is unresolved")
    if status == "AWD":
        return EventDisposition(status, "AWARDED_HOLD", False, False,
                                "awarded result requires independent settlement verification")
    if status == "ABD":
        return EventDisposition(status, "ABANDONED", False, False,
                                "abandoned event is not final-stat eligible")
    return EventDisposition(status, "UNKNOWN", False, False,
                            "unrecognized provider status fails closed")


def game_disposition(game_record: Mapping[str, Any]) -> EventDisposition:
    if not isinstance(game_record, Mapping):
        raise ValueError("game_record mapping required")
    status = game_record.get("status")
    if not isinstance(status, Mapping):
        return classify_game_status(None)
    return classify_game_status(status.get("short"))


def _required_mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} mapping required")
    return value


def _required_int(record: Mapping[str, Any], key: str) -> int:
    value = record.get(key)
    if type(value) is not int:
        raise ValueError(f"{key} integer required")
    return value


def _extract_path(record: Mapping[str, Any], path: Tuple[str, ...]) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            raise ValueError(f"missing player stat field: {'.'.join(path)}")
        value = value[key]
    return value


def _require_nonnegative_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field_name} must be a nonnegative number")
    return float(value)


def _base_ids(game_record: Mapping[str, Any], player_record: Mapping[str, Any]):
    game_id = _required_int(game_record, "id")
    game_ref = _required_mapping(player_record, "game")
    if _required_int(game_ref, "id") != game_id:
        raise ValueError("player statistics game id mismatch")
    team_id = _required_int(_required_mapping(player_record, "team"), "id")
    player_id = _required_int(_required_mapping(player_record, "player"), "id")
    return game_id, team_id, player_id


def _source_record_id(game_id: int, player_id: int, stat: str, retrieved_at: datetime) -> str:
    # Retrieval time intentionally participates so provider stat corrections become
    # distinct revisions instead of being mistaken for duplicate source records.
    return (
        f"apisports-basketball:{game_id}:{player_id}:{stat}:"
        f"{retrieved_at.isoformat()}"
    )


def map_player_statistics(
    game_record: Mapping[str, Any],
    player_record: Mapping[str, Any],
    *,
    outcome_available_at: datetime,
    retrieved_at: datetime,
    stats: Iterable[str] = ("points", "rebounds", "assists",
                            "field_goals", "threepoint_goals", "freethrows_goals"),
) -> List[Dict[str, Any]]:
    """Map one API-Sports player-stat row to generic connector raw records.

    outcome_available_at must come from archived/provider publication evidence or
    another trusted historical availability source. It is never synthesized here.
    """
    disposition = game_disposition(game_record)
    if not disposition.final_stats_eligible:
        return []

    event_time = parse_provider_datetime(game_record.get("date"), "game.date")
    outcome_available_at = _aware(outcome_available_at, "outcome_available_at")
    retrieved_at = _aware(retrieved_at, "retrieved_at")
    if outcome_available_at <= event_time:
        raise ValueError("outcome_available_at must follow event start")
    if retrieved_at < outcome_available_at:
        raise ValueError("retrieved_at cannot precede outcome_available_at")

    game_id, team_id, player_id = _base_ids(game_record, player_record)
    minutes = parse_minutes(player_record.get("minutes"))

    requested = tuple(stats)
    unknown = set(requested) - set(COUNT_STATS) - set(CONVERSION_STATS)
    if unknown:
        raise ValueError(f"unsupported stat fields: {sorted(unknown)}")

    rows: List[Dict[str, Any]] = []
    for stat in requested:
        if stat in COUNT_STATS:
            value = _require_nonnegative_number(
                _extract_path(player_record, COUNT_STATS[stat]), stat)
            opportunity_count = 0  # unknown/not claimed for generic counts
            semantics = "count"
        else:
            block = _required_mapping(player_record, CONVERSION_STATS[stat][0])
            made = _require_nonnegative_number(block.get("total"), f"{stat}.total")
            attempts = block.get("attempts")
            if type(attempts) is not int or attempts < 0:
                raise ValueError(f"{stat}.attempts must be a nonnegative integer")
            if int(made) != made or made > attempts:
                raise ValueError(f"{stat}.total must be integer and <= attempts")
            value = made
            opportunity_count = attempts
            semantics = "successes_of_opportunities"

        rows.append({
            "event_id": str(game_id),
            "player_id": str(player_id),
            "team_id": str(team_id),
            "stat": stat,
            "event_time": event_time.isoformat(),
            "outcome_available_at": outcome_available_at.isoformat(),
            "retrieved_at": retrieved_at.isoformat(),
            "finalized": True,
            "opportunity_count": opportunity_count,
            "outcome_value": value,
            "outcome_semantics": semantics,
            "minutes": minutes,
            "source_record_id": _source_record_id(
                game_id, player_id, stat, retrieved_at),
            "pregame_features": [],
            "provider_game_status": disposition.provider_status,
            "provider_player_type": player_record.get("type"),
            "source_conflict": False,
        })
    return rows


def audit_edge_case_policy(game_record: Mapping[str, Any]) -> Dict[str, Any]:
    """Return an explicit ingest decision for non-happy-path event states."""
    disposition = game_disposition(game_record)
    return {
        "provider_status": disposition.provider_status,
        "category": disposition.category,
        "final_stats_eligible": disposition.final_stats_eligible,
        "settlement_eligible": disposition.settlement_eligible,
        "reason": disposition.reason,
        "midgame_injury_inference_permitted": False,
        "postgame_fact_may_be_backfilled_as_pregame_feature": False,
    }
