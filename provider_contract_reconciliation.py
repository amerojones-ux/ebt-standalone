"""Offline reconciliation across all seven provider contracts.

No network calls or credential reads. This module checks that the machine-readable
provider configs agree with the canonical secret mapping and committed HOLD state.
"""
import json
from pathlib import Path

from provider_preflight import PROVIDERS

ROOT = Path(__file__).resolve().parent

REGISTRY = {
    "RUNDOWN": {
        "path": "config/therundown_access.json",
        "display": "TheRundown",
        "zero_fields": ["authenticated_request_count"],
        "false_fields": ["network_enabled", "forecast_enabled"],
    },
    "SPORTSDATA": {
        "path": "config/sportsdataio_access.json",
        "display": "SportsDataIO",
        "zero_fields": [],
        "false_fields": ["network_enabled", "forecast_enabled"],
    },
    "ODDS": {
        "path": "config/theoddsapi_auth.json",
        "display": "The Odds API",
        "zero_fields": ["request_count"],
        "false_fields": [
            "account_review_verified",
            "explicit_request_approval",
            "network_enabled",
            "forecast_enabled",
            "model_evidence_allowed",
        ],
    },
    "APISPORTS": {
        "path": "config/apisports_status_auth.json",
        "display": "API-Sports",
        "zero_fields": ["request_count"],
        "false_fields": [
            "privacy_rate_limit_review_verified",
            "explicit_request_approval",
            "network_enabled",
            "forecast_enabled",
            "model_evidence_allowed",
        ],
    },
    "RAPID": {
        "path": "config/rapidapi_routing.json",
        "display": "RapidAPI",
        "zero_fields": ["request_count"],
        "false_fields": ["network_enabled", "forecast_enabled"],
    },
    "WEATHER": {
        "path": "config/weatherapi_execution_plan.json",
        "display": "WEATHER",
        "zero_fields": ["max_requests"],
        "false_fields": [
            "network_enabled",
            "explicit_request_approval",
            "entitlement_verified",
            "quota_verified",
            "cost_verified",
            "forecast_enabled",
            "allow_redirects",
            "allow_retries",
        ],
    },
    "SPORTRADAR": {
        "path": "config/sportradar_nfl_auth.json",
        "display": "Sportradar NFL",
        "zero_fields": ["request_count"],
        "false_fields": [
            "network_enabled",
            "quota_impact_approved",
            "forecast_enabled",
        ],
    },
}

def _load(path):
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)

def validate_configs(loader=_load):
    errors = []
    if set(REGISTRY) != set(PROVIDERS):
        errors.append("registry/provider-preflight coverage mismatch")

    for provider_id, spec in REGISTRY.items():
        try:
            config = loader(spec["path"])
        except Exception:
            errors.append(provider_id + " config unreadable")
            continue

        if not isinstance(config, dict):
            errors.append(provider_id + " config must be object")
            continue

        if config.get("secret_name") != PROVIDERS[provider_id]:
            errors.append(provider_id + " secret mapping mismatch")
        if config.get("provider") != spec["display"]:
            errors.append(provider_id + " provider display mismatch")

        for field in spec["false_fields"]:
            if config.get(field) is not False:
                errors.append(provider_id + " " + field + " must be false")

        for field in spec["zero_fields"]:
            value = config.get(field)
            if type(value) is not int or value != 0:
                errors.append(provider_id + " " + field + " must be integer zero")

    return errors

def summary(loader=_load):
    errors = validate_configs(loader)
    return {
        "status": "SAFE_HOLD" if not errors else "INVALID_HOLD",
        "provider_count": len(REGISTRY),
        "error_count": len(errors),
    }
