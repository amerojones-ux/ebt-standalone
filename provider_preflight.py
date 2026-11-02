"""Offline provider-verification preflight. No network or credential access."""
import argparse
import json
import sys

PROVIDERS = {
    "RUNDOWN": "EBT_THERUNDOWN_API_KEY",
    "SPORTSDATA": "EBT_SPORTSDATA_API_KEY",
    "ODDS": "EBT_THEODDS_API_KEY",
    "APISPORTS": "EBT_APISPORTS_API_KEY",
    "RAPID": "EBT_RAPIDAPI_API_KEY",
    "WEATHER": "EBT_WEATHER_API_KEY",
    "SPORTRADAR": "EBT_SPORTRADAR_API_KEY",
}

def validate(plan):
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if plan.get("mode") != "offline":
        errors.append("mode must be offline")
    if plan.get("network_enabled") is not False:
        errors.append("network_enabled must be false")
    if plan.get("forecast_enabled") is not False:
        errors.append("forecast_enabled must be false")
    entries = plan.get("providers")
    if not isinstance(entries, list):
        return errors + ["providers must be a list"]
    seen = set()
    for item in entries:
        if not isinstance(item, dict):
            errors.append("provider entry must be object")
            continue
        name = item.get("name")
        if name not in PROVIDERS:
            errors.append("unknown provider")
            continue
        if name in seen:
            errors.append("duplicate provider: " + name)
        seen.add(name)
        if item.get("secret_name") != PROVIDERS[name]:
            errors.append("secret name mismatch: " + name)
        if item.get("request_count") != 0:
            errors.append("nonzero request count: " + name)
    if seen != set(PROVIDERS):
        errors.append("provider coverage incomplete")
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan")
    args = parser.parse_args()
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    errors = validate(plan)
    print("OFFLINE_PREFLIGHT:", "PASS" if not errors else "HOLD")
    for error in errors:
        print("CHECK:", error)
    print("No network requests or secret reads performed.")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
