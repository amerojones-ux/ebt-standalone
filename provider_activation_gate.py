"""Global provider + model activation gate for Black Diamond.

This module never performs network requests. It evaluates whether a declared
configuration is SAFE_HOLD or eligible for a future activation review.
"""

KNOWN_PROVIDERS = {
    "TheRundown",
    "SportsDataIO",
    "The Odds API",
    "API-Sports",
    "RapidAPI",
    "WeatherAPI",
    "Sportradar",
}
ROLES = {
    "primary_stats",
    "secondary_stats",
    "market_comparison_only",
    "weather_context",
    "aggregator_unresolved",
}
MODEL_GATES = {
    "source_provenance_verified",
    "roster_injury_identity_verified",
    "historical_calibration_verified",
    "joint_dependence_verified",
}

def validate_config(config):
    errors = []
    if not isinstance(config, dict):
        return ["config must be object"]

    if config.get("forecast_enabled") is not False:
        errors.append("forecast_enabled must remain false in committed readiness config")
    if config.get("network_autorun_enabled") is not False:
        errors.append("network autorun must remain false")

    required = config.get("required_providers")
    providers = config.get("providers")
    model = config.get("model_gates")

    if not isinstance(required, list):
        errors.append("required_providers must be list")
        required = []
    if not isinstance(providers, list):
        errors.append("providers must be list")
        providers = []
    if not isinstance(model, dict):
        errors.append("model_gates must be object")
        model = {}

    seen = set()
    by_name = {}
    for entry in providers:
        if not isinstance(entry, dict):
            errors.append("provider entry must be object")
            continue
        name = entry.get("name")
        if name not in KNOWN_PROVIDERS:
            errors.append("unknown provider")
            continue
        if name in seen:
            errors.append("duplicate provider: " + name)
            continue
        seen.add(name)
        by_name[name] = entry

        if entry.get("role") not in ROLES:
            errors.append("invalid role: " + name)
        for key in (
            "contract_ready",
            "live_auth_verified",
            "entitlement_verified",
            "identity_verified",
            "freshness_verified",
            "model_evidence_allowed",
        ):
            if type(entry.get(key)) is not bool:
                errors.append(f"{name} {key} must be boolean")

        if entry.get("role") in ("market_comparison_only", "aggregator_unresolved"):
            if entry.get("model_evidence_allowed") is not False:
                errors.append(name + " cannot be model evidence in current role")

    if seen != KNOWN_PROVIDERS:
        errors.append("provider coverage incomplete")

    if len(required) != len(set(required)):
        errors.append("required_providers contains duplicates")
    for name in required:
        if name not in by_name:
            errors.append("required provider missing: " + str(name))

    for key in MODEL_GATES:
        if type(model.get(key)) is not bool:
            errors.append(key + " must be boolean")

    return errors

def provider_ready(entry):
    if not isinstance(entry, dict):
        return False
    common = all(
        entry.get(key) is True
        for key in (
            "contract_ready",
            "live_auth_verified",
            "entitlement_verified",
            "freshness_verified",
        )
    )
    if not common:
        return False

    role = entry.get("role")
    if role in ("primary_stats", "secondary_stats"):
        return (
            entry.get("identity_verified") is True
            and entry.get("model_evidence_allowed") is True
        )
    if role == "weather_context":
        return True
    if role == "market_comparison_only":
        return entry.get("model_evidence_allowed") is False
    return False

def activation_eligible(config, evidence_ok=False):
    """Evaluate readiness; never changes forecast_enabled itself.

    evidence_ok must come from provider_evidence_gate.evidence_supports_readiness.
    Without that independent evidence check, activation is never eligible.
    """
    if validate_config(config):
        return False
    if evidence_ok is not True:
        return False

    required = config["required_providers"]
    if not required:
        return False

    by_name = {entry["name"]: entry for entry in config["providers"]}
    if not all(provider_ready(by_name[name]) for name in required):
        return False

    required_entries = [by_name[name] for name in required]
    if not any(entry.get("role") == "primary_stats" for entry in required_entries):
        return False

    model = config["model_gates"]
    if not all(model.get(key) is True for key in MODEL_GATES):
        return False

    return True

def status(config, evidence_ok=False):
    return (
        "ELIGIBLE_FOR_MANUAL_ACTIVATION_REVIEW"
        if activation_eligible(config, evidence_ok=evidence_ok)
        else "SAFE_HOLD"
    )
