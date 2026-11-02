"""Offline evidence checks for provider receipts. Not live API verification."""
from datetime import datetime, timezone, timedelta
import re
from extensions.provider_acceptance import validate_receipt

def _parse(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

def assess_provider_evidence(receipt, *, trusted_now, max_age_seconds=3600):
    """Return HOLD or REVIEW_ONLY; never claim provider verification or forecast approval.

    trusted_now must come from the orchestrator, not the provider response.
    """
    base = validate_receipt(receipt)
    now = _parse(trusted_now)
    observed = _parse(receipt["checked_at"])
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or max_age_seconds <= 0:
        raise ValueError("invalid age limit")
    if observed > now + timedelta(seconds=60):
        raise ValueError("future-dated receipt")
    age = (now - observed).total_seconds()
    http_status = receipt.get("http_status")
    record_count = receipt.get("record_count")
    digest = receipt.get("response_sha256")
    data_at = receipt.get("data_as_of")
    evidence_ok = (type(http_status) is int and http_status == 200
                   and type(record_count) is int and record_count > 0
                   and isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
                   and isinstance(data_at, str))
    if evidence_ok:
        as_of = _parse(data_at)
        evidence_ok = as_of <= observed and (observed - as_of).total_seconds() <= max_age_seconds
    review = base["eligible_for_review"] and evidence_ok and 0 <= age <= max_age_seconds
    return {"provider": base["provider"], "endpoint_id": base["endpoint_id"],
            "status": "REVIEW_ONLY" if review else "HOLD",
            "evidence_complete": bool(evidence_ok), "eligible_for_review": bool(review),
            "independently_verified": False, "forecast_approved": False}
