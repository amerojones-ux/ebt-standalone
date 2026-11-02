"""Offline provider acceptance receipt validator. No network calls or secrets."""
from datetime import datetime, timezone

REQUIRED = ("provider", "endpoint_id", "checked_at", "status", "coverage",
            "schema_verified", "rights_verified", "identity_verified",
            "freshness_verified")
VALID_STATUSES = {"PASS", "FAIL", "HOLD"}

def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

def validate_receipt(receipt):
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    for key in REQUIRED:
        if key not in receipt or receipt[key] is None:
            raise ValueError("missing " + key)
    for key in ("provider", "endpoint_id", "coverage"):
        if not isinstance(receipt[key], str) or not receipt[key].strip():
            raise ValueError("invalid " + key)
    _timestamp(receipt["checked_at"])
    if receipt["status"] not in VALID_STATUSES:
        raise ValueError("invalid status")
    for key in ("schema_verified", "rights_verified", "identity_verified", "freshness_verified"):
        if type(receipt[key]) is not bool:
            raise ValueError("verification flag must be boolean")
    forbidden = ("api_key", "token", "authorization", "secret", "password")
    if any(any(word in key.lower() for word in forbidden) for key in receipt):
        raise ValueError("credential-like field forbidden")
    eligible = (receipt["status"] == "PASS" and
                all(receipt[key] for key in ("schema_verified", "rights_verified",
                                             "identity_verified", "freshness_verified")))
    return {"provider": receipt["provider"], "endpoint_id": receipt["endpoint_id"],
            "checked_at": receipt["checked_at"], "eligible_for_review": eligible,
            "forecast_approved": False, "status": "REVIEW_ONLY" if eligible else "HOLD"}
