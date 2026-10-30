"""Offline-only provider integration preflight.

This module deliberately never imports network clients or reads secret values.
It reports unresolved vendor configuration and mandatory security gates.
"""
from __future__ import annotations

import json
from pathlib import Path

from extensions.provider_gateway import PROVIDERS

REQUIRED_GATE_NAMES = (
    "documented_exact_readonly_endpoint",
    "independently_reviewed_hostname_and_auth",
    "protected_secret_environment",
    "infrastructure_egress_allowlist",
    "explicit_execution_approval",
)

def audit_intake(intake: dict) -> dict:
    if not isinstance(intake, dict) or intake.get("schema_version") != 1:
        raise ValueError("unsupported intake schema")
    gates = intake.get("release_gates")
    if not isinstance(gates, dict) or gates.get("forecast") != "HOLD" or gates.get("wager") != "NOT_APPROVED":
        raise ValueError("release gates must remain fail-closed")
    requirements = gates.get("live_probe_requires")
    if not isinstance(requirements, list) or not all(isinstance(x, str) for x in requirements) or not set(REQUIRED_GATE_NAMES).issubset(set(requirements)):
        raise ValueError("missing required probe security gates")
    entries = intake.get("providers")
    if not isinstance(entries, dict) or set(entries) != set(PROVIDERS):
        raise ValueError("seven-provider manifest mismatch")
    report = []
    for name, secret_name in PROVIDERS.items():
        entry = entries[name]
        if not isinstance(entry, dict) or entry.get("secret_name") != secret_name:
            raise ValueError("provider secret mapping mismatch")
        missing = [field for field in ("reviewed_endpoint", "reviewed_auth_scheme", "entitlements")
                   if not isinstance(entry.get(field), str) or entry[field].strip().lower() in ("", "pending", "unknown")]
        if name == "rapidapi" and (not isinstance(entry.get("product"), str) or "pending" in entry["product"]):
            missing.append("subscribed_upstream_product")
        if name == "weather" and (not isinstance(entry.get("product"), str) or "pending" in entry["product"]):
            missing.append("confirmed_weather_vendor")
        # This is intentionally a configuration-only preflight; it can never approve a live probe.
        report.append({"provider": name, "configuration": "INCOMPLETE" if missing else "REVIEW_REQUIRED",
                       "missing": missing, "live_authentication": "NOT_TESTED"})
    return {"mode": "OFFLINE_PREFLIGHT", "forecast": "HOLD", "wager": "NOT_APPROVED",
            "live_probes_executed": False, "providers": report}


def main() -> None:
    # YAML manifest is operator-reviewed separately; JSON input is a local sanitized
    # representation, not a parser for untrusted YAML or a credential source.
    import argparse
    parser = argparse.ArgumentParser(description="Offline-only seven-provider intake preflight")
    parser.add_argument("sanitized_intake_json", type=Path)
    args = parser.parse_args()
    intake = json.loads(args.sanitized_intake_json.read_text(encoding="utf-8"))
    print(json.dumps(audit_intake(intake), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
