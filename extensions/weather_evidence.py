"""Offline weather evidence validation; no HTTP, secrets, or data ingestion."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def validate_pregame_weather_evidence(
    record: Mapping[str, object], *,
    prediction_cutoff_utc: str,
    event_start_utc: str,
    max_forecast_age_hours: int = 24,
) -> dict[str, object]:
    """Fail closed on look-ahead, stale weather, unverified venue and indoor use."""
    result = {"status": "BLOCKED", "forecast": "HOLD",
              "wager": "NOT APPROVED", "weather_feature_eligible": False}
    if not isinstance(record, Mapping):
        return {**result, "reason": "invalid_record"}
    try:
        cutoff = _parse_utc(prediction_cutoff_utc)
        start = _parse_utc(event_start_utc)
        issued = _parse_utc(record.get("issued_at_utc"))
        valid_at = _parse_utc(record.get("valid_at_utc"))
    except ValueError:
        return {**result, "reason": "invalid_timestamp"}
    if type(max_forecast_age_hours) is not int or not 0 < max_forecast_age_hours <= 168:
        return {**result, "reason": "invalid_max_age"}
    if start < cutoff or issued > cutoff or valid_at < issued:
        return {**result, "reason": "temporal_leakage"}
    if (cutoff - issued).total_seconds() > max_forecast_age_hours * 3600:
        return {**result, "reason": "stale_forecast"}
    if abs((valid_at - start).total_seconds()) > 3600:
        return {**result, "reason": "wrong_event_window"}
    if record.get("venue_verified") is not True:
        return {**result, "reason": "unverified_venue"}
    if record.get("venue_type") != "outdoor":
        return {**result, "reason": "non_outdoor_or_unknown_venue"}
    if record.get("provider") != "weather":
        return {**result, "reason": "unverified_source"}
    if record.get("rights_verified") is not True or record.get("feed_verified") is not True:
        return {**result, "reason": "unverified_rights_or_feed"}
    # Passing temporal/venue checks is only feature eligibility, not model certification.
    return {**result, "status": "RESEARCH_ONLY", "reason": "model_validation_pending",
            "weather_feature_eligible": True}
