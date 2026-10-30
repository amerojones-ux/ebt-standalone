"""Offline evidence freshness and reviewer provenance checks.

This is a research-only assessment. Caller-supplied evidence cannot authenticate
its own reviewer, timestamps, rights or vendor identity.
"""
from __future__ import annotations
from datetime import datetime, timezone
from collections.abc import Mapping

def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)

def assess_evidence_freshness(evidence: Mapping[str, object], *,
                              as_of_utc: str, max_age_days: int = 30) -> dict[str, object]:
    if not isinstance(evidence, Mapping):
        raise ValueError("evidence must be a mapping")
    if type(max_age_days) is not int or not 1 <= max_age_days <= 365:
        raise ValueError("invalid maximum age")
    now = _utc(as_of_utc)
    observed = _utc(evidence.get("reviewed_at_utc"))
    age_seconds = (now - observed).total_seconds()
    if age_seconds < 0:
        status = "FUTURE_REVIEW_REJECTED"
    elif age_seconds > max_age_days * 86400:
        status = "STALE_REVIEW"
    else:
        status = "FRESHNESS_ONLY"
    reviewer = evidence.get("reviewer_id")
    evidence_ref = evidence.get("evidence_reference")
    # Neither field establishes identity or authenticity; no values are echoed.
    metadata_present = (isinstance(reviewer, str) and bool(reviewer.strip())
                        and isinstance(evidence_ref, str) and bool(evidence_ref.strip()))
    if not metadata_present:
        status = "MISSING_REVIEW_PROVENANCE"
    return {
        "freshness": status,
        "review_metadata_present": metadata_present,
        "reviewer_authenticated": False,
        "evidence_authenticated": False,
        "provider_rights_verified": False,
        "live_ingestion": "BLOCKED",
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
    }
