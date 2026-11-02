"""Fail-closed live-provider approval gate. Does not perform network requests."""
import argparse
import json
import sys

from provider_preflight import PROVIDERS

REQUIRED = {"product", "host", "path", "auth_method", "quota_per_day", "cost_per_call_usd", "reviewer", "approved_at"}
def validate(register):
    errors = []
    if not isinstance(register, dict):
        return ["register must be object"]
    if register.get("network_enabled") is not False:
        errors.append("network must remain disabled")
    if register.get("forecast_enabled") is not False:
        errors.append("forecast must remain disabled")
    entries = register.get("providers")
    if not isinstance(entries, list):
        return errors + ["providers must be list"]
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("provider entry must be object")
            continue
        name = entry.get("name")
        if name not in PROVIDERS:
            errors.append("unknown provider")
            continue
        if name in seen:
            errors.append("duplicate provider: " + name)
        seen.add(name)
        if entry.get("secret_name") != PROVIDERS[name]:
            errors.append("secret mapping mismatch: " + name)
        if entry.get("approved") is not False:
            errors.append("unapproved provider must be explicitly false: " + name)
        if any(entry.get(k) is not None for k in REQUIRED):
            errors.append("unreviewed metadata must be null: " + name)
    if seen != set(PROVIDERS):
        errors.append("provider coverage incomplete")
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("register")
    args = parser.parse_args()
    with open(args.register, encoding="utf-8") as handle:
        data = json.load(handle)
    errors = validate(data)
    print("LIVE_PROVIDER_GATE:", "SAFE_HOLD" if not errors else "INVALID_HOLD")
    for error in errors:
        print("CHECK:", error)
    print("No network requests or credentials accessed.")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
