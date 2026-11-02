"""Fail-closed seven-provider coverage assessment. Offline only."""
from extensions.provider_evidence_gate import assess_provider_evidence

PROVIDERS = ("TheRundown", "SportsData", "The Odds API", "API-Sports",
             "RapidAPI", "WeatherAPI", "Sportradar")

def assess_coverage(receipts, *, trusted_now, max_age_seconds=3600):
    if not isinstance(receipts, list):
        raise ValueError("receipts must be a list")
    rows = {name: {"status": "HOLD", "reason": "NO_RECEIPT"} for name in PROVIDERS}
    seen = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ValueError("invalid receipt")
        name = receipt.get("provider")
        if name not in rows:
            raise ValueError("unrecognized provider")
        if name in seen:
            raise ValueError("ambiguous duplicate provider")
        seen.add(name)
        result = assess_provider_evidence(receipt, trusted_now=trusted_now,
                                          max_age_seconds=max_age_seconds)
        rows[name] = {"status": result["status"],
                      "reason": "OFFLINE_EVIDENCE_ONLY" if result["eligible_for_review"]
                      else "EVIDENCE_INCOMPLETE"}
    return {"providers": rows, "all_reviewable": all(
        r["status"] == "REVIEW_ONLY" for r in rows.values()),
        "live_connections_verified": False, "forecast_approved": False,
        "status": "HOLD_RESEARCH_ONLY"}
