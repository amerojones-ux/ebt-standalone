"""Conservative research evidence gates; no source or model certification implied."""
from datetime import datetime, timezone

class CertificationHold(ValueError):
    pass

def timestamp(value):
    if not isinstance(value, str):
        raise CertificationHold("timezone-aware timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CertificationHold("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CertificationHold("timezone missing")
    return parsed.astimezone(timezone.utc)

def identity_check(event, player):
    """Verify internal ID consistency, not external identity truth."""
    if not isinstance(event, dict) or not isinstance(player, dict):
        raise CertificationHold("identity objects required")
    teams = event.get("team_ids")
    if not isinstance(teams, (list, tuple)) or len(teams) != 2 or any(not isinstance(x, str) or not x.strip() for x in teams) or teams[0] == teams[1]:
        raise CertificationHold("invalid opposing teams")
    if not isinstance(event.get("event_id"), str) or not event["event_id"].strip():
        raise CertificationHold("event ID missing")
    if not isinstance(player.get("player_id"), str) or not player["player_id"].strip():
        raise CertificationHold("player ID missing")
    if player.get("team_id") not in teams:
        raise CertificationHold("player not mapped to event team")
    if player.get("event_id") != event["event_id"]:
        raise CertificationHold("player event mismatch")
    if player.get("identity_corrob") is not True:
        raise CertificationHold("independent identity corroboration missing")
    # Caller assertions cannot constitute independent certification.
    if not isinstance(player.get("corroboration_capture_ids"), list) or len(player["corroboration_capture_ids"]) < 2 or len(set(player["corroboration_capture_ids"])) < 2:
        raise CertificationHold("two distinct corroboration captures required")
    return True

def availability_check(report, *, cutoff, max_age_seconds):
    if not isinstance(report, dict) or report.get("official_verified") is not True:
        raise CertificationHold("official availability evidence missing")
    if not isinstance(report.get("capture_id"), str) or not report["capture_id"].strip():
        raise CertificationHold("availability capture missing")
    if report.get("status") not in {"available", "out", "questionable", "doubtful", "probable"}:
        raise CertificationHold("unrecognized availability")
    if type(max_age_seconds) is not int or max_age_seconds <= 0:
        raise CertificationHold("invalid freshness limit")
    observed = timestamp(report.get("published_at"))
    retrieved = timestamp(report.get("retrieved_at"))
    deadline = timestamp(cutoff)
    if observed > retrieved or retrieved > deadline or (deadline - observed).total_seconds() > max_age_seconds:
        raise CertificationHold("stale, future, or post-cutoff availability")
    if report["status"] != "available":
        raise CertificationHold("availability requires explicit review")
    return True

def historical_certification(record):
    """Require independent review and temporal integrity, not self-attestation."""
    if not isinstance(record, dict):
        raise CertificationHold("history record required")
    required = ("event_id", "player_id", "team_id", "market_definition", "threshold",
                "source_capture_ids", "model_version", "outcome_source")
    if any(not record.get(k) for k in required):
        raise CertificationHold("missing history provenance")
    captures = record["source_capture_ids"]
    if not isinstance(captures, list) or not captures or any(not isinstance(x, str) or not x.strip() for x in captures):
        raise CertificationHold("invalid capture IDs")
    features = timestamp(record.get("feature_asof"))
    issued = timestamp(record.get("prediction_created_at"))
    start = timestamp(record.get("scheduled_start"))
    finalized = timestamp(record.get("outcome_final_at"))
    if not (features <= issued < start <= finalized):
        raise CertificationHold("temporal leakage or invalid ordering")
    if record.get("certification_status") != "independently_reviewed":
        raise CertificationHold("independent historical certification missing")
    if record.get("outcome_verified") is not True:
        raise CertificationHold("outcome not verified")
    if not isinstance(record.get("outcome_capture_id"), str) or not record["outcome_capture_id"].strip():
        raise CertificationHold("outcome capture missing")
    return True

def release_gate(*, access_authorized=False, history_certified=False,
                 calibration_approved=False, source_verified=False,
                 operational_signoff=False):
    gates = (access_authorized, history_certified, calibration_approved,
             source_verified, operational_signoff)
    if any(x is not True for x in gates):
        return {"status": "HOLD", "forecast_approved": False}
    return {"status": "REVIEW_REQUIRED", "forecast_approved": False}
