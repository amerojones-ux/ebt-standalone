"""Fail-closed readiness gate for automated opportunity discovery.

This module answers only whether the repository has enough verified upstream
coverage to *search* each discovery lane automatically. It never approves a
forecast or wager and it never treats authentication as data entitlement.
"""
from typing import Any, Dict, Iterable

from therundown_access_contract import classify_plan


LANES = ("SAFE_ALT", "ROLE_DISLOCATION", "TAIL_VALUE", "RARE_EVENT")


def _bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field} boolean required")
    return value


def _provider_map(provider_readiness: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(provider_readiness, dict):
        raise ValueError("provider_readiness object required")
    providers = provider_readiness.get("providers")
    if not isinstance(providers, list):
        raise ValueError("provider list required")
    out = {}
    for row in providers:
        if not isinstance(row, dict):
            raise ValueError("provider readiness rows must be objects")
        name = row.get("name")
        if not isinstance(name, str) or not name.strip() or name in out:
            raise ValueError("unique provider name required")
        for field in (
            "contract_ready", "live_auth_verified", "entitlement_verified",
            "identity_verified", "freshness_verified", "model_evidence_allowed",
        ):
            _bool(row.get(field), f"{name}.{field}")
        out[name] = row
    return out


def _live_integrations(module_readiness: Dict[str, Any]) -> Dict[str, bool]:
    if not isinstance(module_readiness, dict):
        raise ValueError("module_readiness object required")
    live = module_readiness.get("live_integrations")
    if not isinstance(live, dict):
        raise ValueError("live_integrations object required")
    required = {
        "sportsbook_quote", "official_slate_and_role",
        "licensed_player_and_team_stats", "calibrated_models", "production_api",
    }
    if set(live) != required:
        raise ValueError("exact live_integrations schema required")
    return {k: _bool(v, f"live_integrations.{k}") for k, v in live.items()}


def _extension(module_readiness: Dict[str, Any], name: str) -> Dict[str, Any]:
    ext = module_readiness.get("extensions")
    if not isinstance(ext, dict) or not isinstance(ext.get(name), dict):
        raise ValueError(f"extension readiness missing: {name}")
    return ext[name]


def _rundown_market_capability(
    provider: Dict[str, Any] | None,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    blockers = []
    if provider is None:
        blockers.append("provider readiness missing")
        return {"provider": "TheRundown", "eligible": False, "blockers": blockers}
    if not isinstance(config, dict):
        raise ValueError("TheRundown config object required")
    info = classify_plan(config.get("plan_name"))
    if not provider["contract_ready"]:
        blockers.append("contract not ready")
    if not provider["live_auth_verified"]:
        blockers.append("live auth not verified")
    if not provider["entitlement_verified"]:
        blockers.append("entitlement not verified")
    if not provider["identity_verified"]:
        blockers.append("identity mapping not verified")
    if not provider["freshness_verified"]:
        blockers.append("freshness not verified")
    if info["props"] is not True:
        blockers.append("configured plan does not include props")
    if info["realtime"] is not True or info["delay_seconds"] != 0:
        blockers.append("configured plan is not verified real-time")
    if config.get("network_enabled") is not True:
        blockers.append("network disabled")
    if config.get("forecast_enabled") is not True:
        blockers.append("forecast use disabled")
    return {
        "provider": "TheRundown",
        "eligible": not blockers,
        "props": info["props"],
        "realtime": info["realtime"],
        "delay_seconds": info["delay_seconds"],
        "blockers": blockers,
    }


def _theoddsapi_market_capability(
    provider: Dict[str, Any] | None,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    blockers = []
    if provider is None:
        return {"provider": "The Odds API", "eligible": False, "blockers": ["provider readiness missing"]}
    if not isinstance(config, dict):
        raise ValueError("The Odds API prop-ladder config object required")
    for field in ("contract_ready", "live_auth_verified", "entitlement_verified",
                  "identity_verified", "freshness_verified"):
        if provider[field] is not True:
            blockers.append(field.replace("_", " ") + " not verified")
    for field, message in (
        ("account_plan_verified", "account plan not verified"),
        ("quota_cost_reviewed", "quota cost not reviewed"),
        ("entitlement_verified", "prop-ladder entitlement not verified"),
        ("identity_mapping_verified", "prop-ladder identity mapping not verified"),
        ("freshness_verified", "prop-ladder freshness not verified"),
        ("market_ladder_route_verified", "event prop-ladder route not verified"),
        ("complete_posted_player_prop_ladder_verified", "complete posted player-prop ladder not verified"),
    ):
        if config.get(field) is not True:
            blockers.append(message)
    if config.get("network_enabled") is not True:
        blockers.append("network disabled")
    if config.get("forecast_enabled") is not True:
        blockers.append("forecast use disabled")
    route = config.get("event_odds_path_template")
    if not isinstance(route, str) or not route.strip():
        blockers.append("event odds route missing")
    discovery_route = config.get("event_markets_path_template")
    if not isinstance(discovery_route, str) or not discovery_route.strip():
        blockers.append("event markets discovery route missing")
    return {
        "provider": "The Odds API",
        "eligible": not blockers,
        "route": route if isinstance(route, str) else None,
        "discovery_route": discovery_route if isinstance(discovery_route, str) else None,
        "blockers": blockers,
    }


def _explicit_market_adapter(
    name: str,
    provider: Dict[str, Any] | None,
    config: Dict[str, Any],
    *,
    route_field: str,
) -> Dict[str, Any]:
    """Require explicit reviewed fields before a generic provider can claim a prop ladder."""
    blockers = []
    if provider is None:
        blockers.append("provider readiness missing")
        return {"provider": name, "eligible": False, "blockers": blockers}
    if not isinstance(config, dict):
        raise ValueError(f"{name} config object required")
    for field in ("contract_ready", "live_auth_verified", "entitlement_verified",
                  "identity_verified", "freshness_verified"):
        if provider[field] is not True:
            blockers.append(field.replace("_", " ") + " not verified")
    if config.get("network_enabled") is not True:
        blockers.append("network disabled")
    if config.get("forecast_enabled") is not True:
        blockers.append("forecast use disabled")
    if config.get("market_ladder_verified") is not True:
        blockers.append("market ladder route not verified")
    if config.get("complete_player_prop_ladder_verified") is not True:
        blockers.append("complete player-prop ladder not verified")
    route = config.get(route_field)
    if not isinstance(route, str) or not route.strip():
        blockers.append("exact market route missing")
    return {
        "provider": name,
        "eligible": not blockers,
        "route": route if isinstance(route, str) else None,
        "blockers": blockers,
    }


def assess_discovery_readiness(
    provider_readiness: Dict[str, Any],
    module_readiness: Dict[str, Any],
    *,
    therundown_access: Dict[str, Any],
    theoddsapi_prop_ladder: Dict[str, Any],
    rapidapi_routing: Dict[str, Any],
) -> Dict[str, Any]:
    """Return automated discovery coverage, never candidate or wager approval."""
    providers = _provider_map(provider_readiness)
    live = _live_integrations(module_readiness)

    market_sources = [
        _rundown_market_capability(providers.get("TheRundown"), therundown_access),
        _theoddsapi_market_capability(
            providers.get("The Odds API"), theoddsapi_prop_ladder),
        _explicit_market_adapter(
            "RapidAPI", providers.get("RapidAPI"), rapidapi_routing,
            route_field="probe_endpoint"),
    ]
    eligible_market_sources = [x["provider"] for x in market_sources if x["eligible"]]

    market_ladder_ready = bool(eligible_market_sources) and live["sportsbook_quote"]
    role_ready = live["official_slate_and_role"]
    stats_ready = live["licensed_player_and_team_stats"]
    calibration_ready = live["calibrated_models"]

    alt_ext = _extension(module_readiness, "alternate_line_opportunity_discovery")
    role_ext = _extension(module_readiness, "role_reallocation_trigger")
    rare_ext = _extension(module_readiness, "rare_event_asymmetric_value")

    lanes = {
        "SAFE_ALT": {
            "engine_implemented": alt_ext.get("code") == "implemented",
            "automated_input_ready": (
                alt_ext.get("code") == "implemented"
                and market_ladder_ready and role_ready and stats_ready
            ),
            "requires": ["complete_verified_market_ladder", "official_role", "independent_stats_distribution"],
        },
        "ROLE_DISLOCATION": {
            "engine_implemented": role_ext.get("code") == "implemented",
            "automated_input_ready": (
                role_ext.get("code") == "implemented" and role_ready and stats_ready
            ),
            "requires": ["official_role", "independent_stats_distribution"],
        },
        "TAIL_VALUE": {
            "engine_implemented": alt_ext.get("code") == "implemented",
            "automated_input_ready": (
                alt_ext.get("code") == "implemented"
                and market_ladder_ready and stats_ready
            ),
            "requires": ["complete_verified_market_ladder", "independent_stats_distribution"],
        },
        "RARE_EVENT": {
            "engine_implemented": rare_ext.get("code") == "implemented",
            "automated_input_ready": (
                rare_ext.get("code") == "implemented"
                and market_ladder_ready and role_ready and stats_ready
            ),
            "requires": ["complete_verified_market_ladder", "official_role", "dedicated_rare_event_distribution"],
        },
    }

    blockers = []
    if not eligible_market_sources:
        blockers.append("NO_ELIGIBLE_REALTIME_COMPLETE_PROP_LADDER_SOURCE")
    if not live["sportsbook_quote"]:
        blockers.append("SPORTSBOOK_QUOTE_INTEGRATION_DISABLED")
    if not role_ready:
        blockers.append("OFFICIAL_SLATE_ROLE_INTEGRATION_DISABLED")
    if not stats_ready:
        blockers.append("LICENSED_PLAYER_TEAM_STATS_INTEGRATION_DISABLED")
    if not calibration_ready:
        blockers.append("CALIBRATED_MODELS_NOT_VERIFIED")

    all_automated = all(x["automated_input_ready"] for x in lanes.values())
    return {
        "mode": "AUTOMATED_OPPORTUNITY_DISCOVERY_READINESS",
        "status": "READY_FOR_AUTOMATED_RESEARCH" if all_automated else "SAFE_HOLD",
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "candidate_qualification_still_required": True,
        "market_ladder_ready": market_ladder_ready,
        "eligible_market_sources": eligible_market_sources,
        "market_source_diagnostics": market_sources,
        "official_role_ready": role_ready,
        "independent_stats_ready": stats_ready,
        "calibration_ready": calibration_ready,
        "lanes": lanes,
        "blockers": blockers,
        "note": (
            "Discovery readiness only establishes whether the platform can search the lane. "
            "Every candidate must still pass V7/V7.1 evidence, calibration, MC, price, "
            "scenario and final revalidation gates."
        ),
    }
