"""Fail-closed validation of externally supplied NBA event records.

This validates record structure only; it never authenticates a provider or
certifies a prediction. Call only after permitted capture and provenance checks.
"""
from datetime import datetime, timezone

class EvidenceHold(ValueError):
    """Input cannot qualify for independent evidence review."""


def _timestamp(value):
    if not isinstance(value, str) or not value:
        raise EvidenceHold("missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceHold("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceHold("timestamp must have timezone")
    return parsed.astimezone(timezone.utc)


def validate_event_record(record):
    """Return canonical identifiers, or raise EvidenceHold.

    Prevents deleted games, missing identifiers, duplicate player IDs,
    invalid time ordering and malformed team participation from entering
    downstream candidate generation. No forecast approval is returned.
    """
    if not isinstance(record, dict):
        raise EvidenceHold("event must be an object")
    if record.get("deleted") is True:
        raise EvidenceHold("deleted game")
    if not isinstance(record.get("event_id"), str) or not record["event_id"].strip():
        raise EvidenceHold("missing event ID")
    scheduled = _timestamp(record.get("scheduled_start"))
    effective = _timestamp(record.get("effective_at"))
    fetched = _timestamp(record.get("fetched_at"))
    if effective > fetched:
        raise EvidenceHold("effective time later than capture")
    if record.get("status") not in {"scheduled", "inprogress", "closed"}:
        raise EvidenceHold("unrecognized status")
    teams = record.get("teams")
    if not isinstance(teams, list) or len(teams) != 2:
        raise EvidenceHold("exactly two teams required")
    ids = []
    for team in teams:
        if not isinstance(team, dict) or not isinstance(team.get("team_id"), str) or not team["team_id"].strip():
            raise EvidenceHold("missing team ID")
        ids.append(team["team_id"])
    if len(set(ids)) != 2:
        raise EvidenceHold("duplicate team ID")
    if record["status"] == "scheduled" and fetched >= scheduled:
        raise EvidenceHold("scheduled status captured after start: needs revalidation")
    if record.get("deleted_games") is not None:
        removed = record["deleted_games"]
        if not isinstance(removed, list) or any(not isinstance(x, str) for x in removed):
            raise EvidenceHold("invalid deleted_games")
        if record["event_id"] in removed:
            raise EvidenceHold("event removed from schedule")
    return {"event_id": record["event_id"], "team_ids": tuple(ids), "status": record["status"]}
