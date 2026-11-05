"""SportsDataIO NBA historical final-box-score mapping.

SportsDataIO is treated as high-trust provider/reference evidence under V7, not
as A1 official league/team evidence. The official NBA source remains the A1
settlement anchor.

For historical backfills, PlayerGame.Updated is used conservatively as the
outcome availability timestamp. This may reject some observations earlier than
necessary, but cannot move a later correction backward in time.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PROVIDER_ID = "SPORTSDATAIO_NBA"
EASTERN = ZoneInfo("America/New_York")

FINAL_STATUSES = {"Final", "F/OT"}
NONFINAL_STATUSES = {
    "Scheduled", "InProgress", "Suspended", "Postponed",
    "Delayed", "Canceled", "NotNecessary",
}
HOLD_STATUSES = {"Forfeit"}

COUNT_FIELDS = {
    "points": "Points",
    "rebounds": "Rebounds",
    "assists": "Assists",
    "steals": "Steals",
    "blocked_shots": "BlockedShots",
    "turnovers": "Turnovers",
}
CONVERSION_FIELDS = {
    "field_goals": ("FieldGoalsMade", "FieldGoalsAttempted"),
    "threepoint_goals": ("ThreePointersMade", "ThreePointersAttempted"),
    "freethrows_goals": ("FreeThrowsMade", "FreeThrowsAttempted"),
}


def parse_sportsdataio_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO-8601") from exc
    else:
        raise ValueError(f"{field_name} datetime required")
    if dt.tzinfo is None or dt.utcoffset() is None:
        dt = dt.replace(tzinfo=EASTERN)
    return dt


def classify_game_status(status: Any) -> Dict[str, Any]:
    if status in FINAL_STATUSES:
        return {
            "category": "FINAL",
            "final_stats_eligible": True,
            "settlement_eligible": True,
            "reason": "normal completed game",
        }
    if status in HOLD_STATUSES:
        return {
            "category": "FORFEIT_HOLD",
            "final_stats_eligible": False,
            "settlement_eligible": False,
            "reason": "forfeit requires official NBA settlement verification",
        }
    if status in NONFINAL_STATUSES:
        return {
            "category": str(status).upper(),
            "final_stats_eligible": False,
            "settlement_eligible": False,
            "reason": "game is not a normal final-stat settlement",
        }
    return {
        "category": "UNKNOWN",
        "final_stats_eligible": False,
        "settlement_eligible": False,
        "reason": "unrecognized SportsDataIO game status fails closed",
    }


def _nonnegative_number(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is missing")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field_name} must be nonnegative numeric")
    return float(value)


def _nonnegative_intlike(value: Any, field_name: str) -> int:
    number = _nonnegative_number(value, field_name)
    if int(number) != number:
        raise ValueError(f"{field_name} must be integer-valued")
    return int(number)


def _event_provider_id(game: Mapping[str, Any]) -> str:
    global_id = game.get("GlobalGameID")
    if global_id is not None:
        return f"global:{global_id}"
    game_id = game.get("GameID")
    if game_id is None:
        raise ValueError("GameID or GlobalGameID required")
    return f"game:{game_id}"


def _player_game_event_id(player_game: Mapping[str, Any], game: Mapping[str, Any]) -> str:
    pg_global = player_game.get("GlobalGameID")
    if pg_global is not None and game.get("GlobalGameID") is not None:
        if str(pg_global) != str(game["GlobalGameID"]):
            raise ValueError("PlayerGame GlobalGameID mismatch")
    pg_game = player_game.get("GameID")
    if pg_game is not None and game.get("GameID") is not None:
        if str(pg_game) != str(game["GameID"]):
            raise ValueError("PlayerGame GameID mismatch")
    return _event_provider_id(game)


def map_box_score(
    box_score: Mapping[str, Any], *, retrieved_at: datetime,
    stats: Iterable[str] = (
        "points", "rebounds", "assists",
        "field_goals", "threepoint_goals", "freethrows_goals",
    ),
) -> List[Dict[str, Any]]:
    if not isinstance(box_score, Mapping):
        raise ValueError("box_score mapping required")
    game = box_score.get("Game")
    player_games = box_score.get("PlayerGames")
    if not isinstance(game, Mapping):
        raise ValueError("BoxScore.Game mapping required")
    if not isinstance(player_games, list):
        raise ValueError("BoxScore.PlayerGames list required")

    disposition = classify_game_status(game.get("Status"))
    if not disposition["final_stats_eligible"]:
        return []

    event_time = parse_sportsdataio_datetime(game.get("DateTime"), "Game.DateTime")
    retrieved_at = parse_sportsdataio_datetime(retrieved_at, "retrieved_at")

    requested = tuple(stats)
    unsupported = set(requested) - set(COUNT_FIELDS) - set(CONVERSION_FIELDS)
    if unsupported:
        raise ValueError(f"unsupported SportsDataIO stats: {sorted(unsupported)}")

    rows: List[Dict[str, Any]] = []
    for player_game in player_games:
        if not isinstance(player_game, Mapping):
            raise ValueError("PlayerGame mapping required")
        if player_game.get("IsGameOver") is not True:
            raise ValueError("final endpoint returned PlayerGame IsGameOver != true")

        event_provider_id = _player_game_event_id(player_game, game)
        player_id = player_game.get("PlayerID")
        team_id = player_game.get("TeamID")
        if player_id is None or team_id is None:
            raise ValueError("PlayerID and TeamID required")

        updated_raw = player_game.get("Updated") or game.get("Updated")
        updated_at = parse_sportsdataio_datetime(updated_raw, "PlayerGame.Updated")
        if updated_at <= event_time:
            raise ValueError("Updated must follow game start")
        if retrieved_at < updated_at:
            raise ValueError("retrieved_at cannot precede provider Updated")

        minutes_raw = player_game.get("Minutes")
        minutes = None if minutes_raw is None else float(
            _nonnegative_number(minutes_raw, "Minutes"))

        for stat in requested:
            if stat in COUNT_FIELDS:
                value = _nonnegative_number(player_game.get(COUNT_FIELDS[stat]), stat)
                opportunity_count = 0
                semantics = "count"
            else:
                made_field, attempt_field = CONVERSION_FIELDS[stat]
                made = _nonnegative_intlike(player_game.get(made_field), made_field)
                attempts = _nonnegative_intlike(
                    player_game.get(attempt_field), attempt_field)
                if made > attempts:
                    raise ValueError(f"{made_field} cannot exceed {attempt_field}")
                value = float(made)
                opportunity_count = attempts
                semantics = "successes_of_opportunities"

            rows.append({
                "event_id": event_provider_id,
                "player_id": str(player_id),
                "team_id": str(team_id),
                "player_name": str(player_game.get("Name") or ""),
                "stat": stat,
                "event_time": event_time.isoformat(),
                "outcome_available_at": updated_at.isoformat(),
                "retrieved_at": retrieved_at.isoformat(),
                "finalized": True,
                "opportunity_count": opportunity_count,
                "outcome_value": value,
                "outcome_semantics": semantics,
                "minutes": minutes,
                "source_record_id": (
                    f"sportsdataio:{event_provider_id}:{player_id}:{stat}:"
                    f"{updated_at.isoformat()}"
                ),
                "pregame_features": [],
                "provider_game_status": game.get("Status"),
                "provider_game_id": game.get("GameID"),
                "provider_global_game_id": game.get("GlobalGameID"),
                "provider_stat_id": player_game.get("StatID"),
                "provider_updated_at": updated_at.isoformat(),
                "source_conflict": False,
            })
    return rows


def extract_player_crossrefs(player_profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Return only documented stable cross-reference IDs."""
    if not isinstance(player_profile, Mapping):
        raise ValueError("player_profile mapping required")
    fields = {
        "sportsdataio_player_id": player_profile.get("PlayerID"),
        "sportradar_player_id": player_profile.get("SportRadarPlayerID"),
        "rotowire_player_id": player_profile.get("RotoWirePlayerID"),
        "stats_player_id": player_profile.get("StatsPlayerID"),
        "sportsdirect_player_id": player_profile.get("SportsDirectPlayerID"),
    }
    return {key: value for key, value in fields.items()
            if value is not None and value != ""}


def event_resolution_fingerprint(game: Mapping[str, Any]) -> Dict[str, Any]:
    """Descriptive event evidence for manual/provider-map resolution only."""
    if not isinstance(game, Mapping):
        raise ValueError("game mapping required")
    return {
        "provider_event_id": _event_provider_id(game),
        "event_time": parse_sportsdataio_datetime(
            game.get("DateTime"), "Game.DateTime").isoformat(),
        "away_team": game.get("AwayTeam"),
        "home_team": game.get("HomeTeam"),
        "away_team_id": game.get("AwayTeamID"),
        "home_team_id": game.get("HomeTeamID"),
        "global_away_team_id": game.get("GlobalAwayTeamID"),
        "global_home_team_id": game.get("GlobalHomeTeamID"),
    }
