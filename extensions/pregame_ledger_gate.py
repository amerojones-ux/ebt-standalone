"""Fail-closed offline pregame forecast record validation. No model certification."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

REQUIRED = ("forecast_id", "event_id", "subject_id", "competition", "market",
            "comparator", "threshold", "probability", "model_version",
            "source_hash", "issued_at", "event_start")

def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(timezone.utc)

def validate_pregame_record(record):
    """Return normalized validated record or raise ValueError; never approve a bet."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    for key in REQUIRED:
        if key not in record or record[key] is None or record[key] == "":
            raise ValueError("missing required field: " + key)
    for key in ("forecast_id", "event_id", "subject_id", "competition",
                "market", "model_version", "source_hash"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError("invalid identity: " + key)
    if record["comparator"] not in ("GT", "GE", "LT", "LE"):
        raise ValueError("invalid comparator")
    try:
        line = Decimal(str(record["threshold"]))
        probability = Decimal(str(record["probability"]))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid numeric input") from exc
    if not line.is_finite() or not probability.is_finite() or not 0 <= probability <= 1:
        raise ValueError("invalid numeric range")
    if _instant(record["issued_at"]) >= _instant(record["event_start"]):
        raise ValueError("forecast must precede event start")
    if "source_effective_at" in record and _instant(record["source_effective_at"]) > _instant(record["issued_at"]):
        raise ValueError("future information leakage")
    if record.get("forecast_approved") is True or record.get("wager_approved") is True:
        raise ValueError("research record cannot assert approval")
    return dict(record, threshold=str(line), probability=str(probability),
                forecast_approved=False, wager_approved=False, status="HOLD_RESEARCH_ONLY")
