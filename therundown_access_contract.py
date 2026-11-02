"""Offline TheRundown v2 access/billing contract. No network or secrets."""

PLANS = {
    "FREE": {"delay_seconds": 300, "realtime": False, "props": False, "websocket": False},
    "STARTER": {"delay_seconds": 60, "realtime": False, "props": True, "websocket": False},
    "PRO": {"delay_seconds": 30, "realtime": False, "props": True, "websocket": False},
    "ULTRA": {"delay_seconds": 0, "realtime": True, "props": True, "websocket": True},
    "SUPER": {"delay_seconds": 0, "realtime": True, "props": True, "websocket": True},
    "MEGA": {"delay_seconds": 0, "realtime": True, "props": True, "websocket": True},
    "MAX": {"delay_seconds": 0, "realtime": True, "props": True, "websocket": True},
    "ENTERPRISE": {"delay_seconds": None, "realtime": False, "props": False, "websocket": False},
    "UNKNOWN": {"delay_seconds": None, "realtime": False, "props": False, "websocket": False},
}

PUBLIC_REFERENCE_PATHS = {"/api/v2/sports", "/api/v2/affiliates"}

def classify_plan(name):
    if not isinstance(name, str):
        return PLANS["UNKNOWN"]
    return PLANS.get(name.strip().upper(), PLANS["UNKNOWN"])

def validate_plan(plan):
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be object"]
    if plan.get("provider") != "TheRundown":
        errors.append("provider mismatch")
    if plan.get("secret_name") != "EBT_THERUNDOWN_API_KEY":
        errors.append("secret mapping mismatch")
    if plan.get("auth_header") != "X-TheRundown-Key":
        errors.append("auth header mismatch")
    if plan.get("base_url") != "https://therundown.io/api/v2":
        errors.append("base URL mismatch")
    plan_name = plan.get("plan_name")
    if plan_name not in PLANS or plan_name == "UNKNOWN":
        errors.append("exact plan must be reviewed")
    if plan.get("data_delay_verified") is not True:
        errors.append("data delay must be verified")
    if plan.get("datapoint_quota_reviewed") is not True:
        errors.append("data-point quota must be reviewed")
    if plan.get("overage_behavior_reviewed") is not True:
        errors.append("overage behavior must be reviewed")
    if plan.get("network_enabled") is not False:
        errors.append("network must remain disabled")
    if plan.get("authenticated_request_count") != 0:
        errors.append("authenticated request count must be zero")
    if plan.get("forecast_enabled") is not False:
        errors.append("forecast must remain disabled")
    return errors

def is_public_reference_path(path):
    return isinstance(path, str) and path in PUBLIC_REFERENCE_PATHS

def can_use_for_live_model_evidence(plan_name, response_delay_seconds=None, identity_verified=False, freshness_verified=False):
    info = classify_plan(plan_name)
    if not info["realtime"]:
        return False
    if response_delay_seconds != 0:
        return False
    return bool(identity_verified and freshness_verified)

def can_authorize_authenticated_request(plan):
    """This offline phase never authorizes a metered key-bearing request."""
    return False
