"""Fail-closed authorization gate for future WeatherAPI live probes. No network."""
import json
import sys

REQUIRED = {"provider", "network_enabled", "explicit_request_approval", "entitlement_verified", "quota_verified", "cost_verified", "forecast_enabled", "max_requests", "timeout_seconds", "allow_redirects", "allow_retries"}

def validate(plan):
    if not isinstance(plan, dict):
        return ["plan must be object"]
    errors = []
    if set(plan) != REQUIRED:
        errors.append("unexpected or missing fields")
    if plan.get("provider") != "WEATHER":
        errors.append("provider must be WEATHER")
    for key in ("network_enabled", "explicit_request_approval", "entitlement_verified", "quota_verified", "cost_verified", "forecast_enabled", "allow_redirects", "allow_retries"):
        if plan.get(key) is not False:
            errors.append(key + " must be false")
    if type(plan.get("max_requests")) is not int or plan["max_requests"] != 0:
        errors.append("max_requests must be zero")
    if type(plan.get("timeout_seconds")) is not int or not 1 <= plan["timeout_seconds"] <= 10:
        errors.append("invalid timeout")
    return errors

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        errors=validate(json.load(f))
    print("WEATHERAPI_EXECUTION_GATE:", "SAFE_HOLD" if not errors else "INVALID_HOLD")
    for error in errors: print("CHECK:",error)
    print("No network or credentials accessed.")
    sys.exit(bool(errors))
