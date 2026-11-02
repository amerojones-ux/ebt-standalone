"""Offline SportsDataIO access-tier classification. No network or secrets."""

ACCESS_METHODS = {
    "FREE_TRIAL": {
        "data_class": "scrambled",
        "live_current": False,
        "historical_real": False,
        "model_evidence_allowed": False,
        "notes": "Integration/schema testing only; provider documents scrambled data.",
    },
    "DEV_KEY": {
        "data_class": "scrambled",
        "live_current": False,
        "historical_real": False,
        "model_evidence_allowed": False,
        "notes": "Unlimited integration-scale testing but still scrambled.",
    },
    "REPLAY": {
        "data_class": "real_historical_replay",
        "live_current": False,
        "historical_real": True,
        "model_evidence_allowed": False,
        "notes": "Authentic past games replayed on a live-like schedule; not current-day evidence.",
    },
    "DISCOVERY_LAB_FREE": {
        "data_class": "real_last_season",
        "live_current": False,
        "historical_real": True,
        "model_evidence_allowed": False,
        "notes": "Real but last-season data only.",
    },
    "DISCOVERY_LAB_PAID": {
        "data_class": "real_next_day_delayed",
        "live_current": False,
        "historical_real": True,
        "model_evidence_allowed": False,
        "notes": "Real data delayed by one day; not live current-day evidence.",
    },
    "LEAGUES_PRODUCTION": {
        "data_class": "potential_live_production",
        "live_current": True,
        "historical_real": True,
        "model_evidence_allowed": False,
        "notes": "Potentially live/real, but account entitlement and feed scope must be separately verified.",
    },
    "GLOBAL_PRODUCTION": {
        "data_class": "potential_live_topline",
        "live_current": True,
        "historical_real": True,
        "model_evidence_allowed": False,
        "notes": "Potentially live schedules/scores; deep prop/stat evidence not implied.",
    },
    "UNKNOWN": {
        "data_class": "unknown",
        "live_current": False,
        "historical_real": False,
        "model_evidence_allowed": False,
        "notes": "Fail closed until product/tier is identified.",
    },
}

def classify_access(method):
    if not isinstance(method, str):
        return ACCESS_METHODS["UNKNOWN"]
    return ACCESS_METHODS.get(method.strip().upper(), ACCESS_METHODS["UNKNOWN"])

def validate_auth_config(config):
    """Require header auth; forbid query-string keys for Black Diamond integrations."""
    errors = []
    if not isinstance(config, dict):
        return ["config must be object"]
    if config.get("secret_name") != "EBT_SPORTSDATA_API_KEY":
        errors.append("secret mapping mismatch")
    if config.get("auth_header") != "Ocp-Apim-Subscription-Key":
        errors.append("auth header mismatch")
    if config.get("allow_query_key") is not False:
        errors.append("query-string key auth must be disabled")
    if config.get("network_enabled") is not False:
        errors.append("network must remain disabled")
    if config.get("forecast_enabled") is not False:
        errors.append("forecast must remain disabled")
    return errors

def can_promote_to_model_evidence(method, entitlement_verified=False, feed_verified=False, freshness_verified=False):
    """No SportsDataIO source is model evidence until all production gates are independently proven."""
    info = classify_access(method)
    if method not in ("LEAGUES_PRODUCTION", "GLOBAL_PRODUCTION"):
        return False
    if not info["live_current"]:
        return False
    return bool(entitlement_verified and feed_verified and freshness_verified)
