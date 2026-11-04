"""Fail-closed account/precondition gates for providers without live probe workflows.

No secrets, network access, or provider requests. A provider becoming fully
specified returns IMPLEMENTATION_REQUIRED so CI blocks until a hardened
one-shot workflow is reviewed and registered.
"""
import json
from pathlib import Path
import urllib.parse

from sportsdataio_access_contract import ACCESS_METHODS
from rapidapi_routing_contract import PRICING_TYPES

ROOT=Path(__file__).resolve().parent

FILES={
    "SportsDataIO":"config/sportsdataio_access.json",
    "Sportradar":"config/sportradar_nfl_auth.json",
    "RapidAPI":"config/rapidapi_routing.json",
}

PLANNED_AUTHORIZATIONS={
    "SportsDataIO":{
        "review":"I_CONFIRM_SPORTSDATAIO_ACCESS_TIER_FEED_AND_QUOTA_REVIEWED",
        "request":"I_APPROVE_ONE_SPORTSDATAIO_AUTHENTICATED_REQUEST",
    },
    "Sportradar":{
        "review":"I_CONFIRM_SPORTRADAR_NFL_ACCESS_LEVEL_PRODUCT_AND_QUOTA_REVIEWED",
        "request":"I_APPROVE_ONE_SPORTRADAR_NFL_HIERARCHY_REQUEST",
    },
    "RapidAPI":{
        "review":"I_CONFIRM_RAPIDAPI_PRODUCT_HOST_PLAN_QUOTA_AND_OVERAGE_REVIEWED",
        "request":"I_APPROVE_ONE_RAPIDAPI_PROVIDER_REQUEST",
    },
}

def _load(path):
    with (ROOT/path).open(encoding="utf-8") as handle:
        return json.load(handle)

def _result(provider,safety_errors,blockers):
    if safety_errors:
        status="INVALID_HOLD"
    elif blockers:
        status="BLOCKED_PRECONDITION"
    else:
        status="IMPLEMENTATION_REQUIRED"
    return {
        "provider":provider,
        "status":status,
        "safety_errors":safety_errors,
        "blockers":blockers,
        "planned_authorizations":PLANNED_AUTHORIZATIONS[provider],
        "network_request_permitted":False,
        "secret_access_permitted":False,
        "forecast_activation_permitted":False,
    }

def assess_therundown(cfg):
    safety=[]
    blockers=[]
    expected={
        "provider":"TheRundown",
        "secret_name":"EBT_THERUNDOWN_API_KEY",
        "auth_header":"X-TheRundown-Key",
        "base_url":"https://therundown.io/api/v2",
        "network_enabled":False,
        "authenticated_request_count":0,
        "forecast_enabled":False,
    }
    for key,value in expected.items():
        if cfg.get(key)!=value:
            safety.append(key+" safety mismatch")
    if cfg.get("plan_name") in (None,"","UNKNOWN"):
        blockers.append("exact account plan not reviewed")
    if cfg.get("data_delay_verified") is not True:
        blockers.append("account data delay not verified")
    if cfg.get("datapoint_quota_reviewed") is not True:
        blockers.append("data-point quota not reviewed")
    if cfg.get("overage_behavior_reviewed") is not True:
        blockers.append("overage behavior not reviewed")
    return _result("TheRundown",safety,blockers)

def _sportsdata_endpoint_ok(value):
    if not isinstance(value,str) or not value:
        return False
    parsed=urllib.parse.urlsplit(value)
    if parsed.scheme!="https" or parsed.hostname!="api.sportsdata.io":
        return False
    if not parsed.path.startswith("/v3/"):
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    if parsed.port is not None or parsed.fragment:
        return False
    query=urllib.parse.parse_qs(parsed.query,keep_blank_values=True)
    return "key" not in {k.lower() for k in query}

def assess_sportsdataio(cfg):
    safety=[]
    blockers=[]
    expected={
        "provider":"SportsDataIO",
        "secret_name":"EBT_SPORTSDATA_API_KEY",
        "auth_header":"Ocp-Apim-Subscription-Key",
        "allow_query_key":False,
        "network_enabled":False,
        "forecast_enabled":False,
    }
    for key,value in expected.items():
        if cfg.get(key)!=value:
            safety.append(key+" safety mismatch")
    method=cfg.get("declared_access_method")
    if method not in ACCESS_METHODS or method=="UNKNOWN":
        blockers.append("exact SportsDataIO access mode not classified")
    product=cfg.get("probe_product")
    if not isinstance(product,str) or not product.strip():
        blockers.append("exact subscribed API product not identified")
    endpoint=cfg.get("probe_endpoint")
    if not _sportsdata_endpoint_ok(endpoint):
        blockers.append("exact header-auth probe endpoint not reviewed")
    if cfg.get("quota_reviewed") is not True:
        blockers.append("request quota not reviewed")
    if cfg.get("overage_reviewed") is not True:
        blockers.append("overage behavior not reviewed")
    return _result("SportsDataIO",safety,blockers)

def _sportradar_endpoint_ok(value,access_level):
    if access_level not in {"trial","production"}:
        return False
    expected=(
        "https://api.sportradar.com/nfl/official/"
        +access_level+
        "/v7/en/league/hierarchy.json"
    )
    return value==expected

def assess_sportradar(cfg):
    safety=[]
    blockers=[]
    expected={
        "provider":"Sportradar NFL",
        "secret_name":"EBT_SPORTRADAR_API_KEY",
        "auth_header":"x-api-key",
        "host":"api.sportradar.com",
        "version":"v7",
        "language":"en",
        "format":"json",
        "network_enabled":False,
        "quota_impact_approved":False,
        "request_count":0,
        "forecast_enabled":False,
    }
    for key,value in expected.items():
        if cfg.get(key)!=value:
            safety.append(key+" safety mismatch")
    access=cfg.get("access_level")
    if access not in {"trial","production"}:
        blockers.append("NFL access level must be explicitly trial or production")
    if cfg.get("product_verified") is not True:
        blockers.append("NFL product/package not verified in account")
    if cfg.get("quota_reviewed") is not True:
        blockers.append("rolling quota and QPS not reviewed")
    if not _sportradar_endpoint_ok(cfg.get("probe_endpoint"),access):
        blockers.append("access-level-specific League Hierarchy endpoint not reviewed")
    return _result("Sportradar",safety,blockers)

def assess_rapidapi(cfg):
    safety=[]
    blockers=[]
    expected={
        "provider":"RapidAPI",
        "secret_name":"EBT_RAPIDAPI_API_KEY",
        "key_header":"X-RapidAPI-Key",
        "host_header":"X-RapidAPI-Host",
        "network_enabled":False,
        "request_count":0,
        "forecast_enabled":False,
    }
    for key,value in expected.items():
        if cfg.get(key)!=value:
            safety.append(key+" safety mismatch")

    product=cfg.get("api_product")
    if not isinstance(product,str) or not product.strip():
        blockers.append("exact RapidAPI product not identified")
    host=cfg.get("rapidapi_host")
    if not isinstance(host,str) or "." not in host:
        blockers.append("exact X-RapidAPI-Host not identified")
    pricing=cfg.get("pricing_type")
    if pricing not in PRICING_TYPES or pricing=="UNKNOWN":
        blockers.append("pricing type not reviewed")
    if not isinstance(cfg.get("plan_name"),str) or not cfg.get("plan_name").strip():
        blockers.append("subscription plan not identified")
    if not isinstance(cfg.get("billing_object"),str) or not cfg.get("billing_object").strip():
        blockers.append("billing object not identified")
    for key,label in (
        ("subscription_verified","subscription not verified"),
        ("quota_reviewed","quota not reviewed"),
        ("overage_reviewed","overage behavior not reviewed"),
        ("endpoint_reviewed","exact endpoint not reviewed"),
    ):
        if cfg.get(key) is not True:
            blockers.append(label)
    return _result("RapidAPI",safety,blockers)

ASSESSORS={
    "SportsDataIO":assess_sportsdataio,
    "Sportradar":assess_sportradar,
    "RapidAPI":assess_rapidapi,
}

def assess_all(*,loader=_load):
    results=[]
    for provider,path in FILES.items():
        try:
            cfg=loader(path)
        except Exception:
            results.append(_result(provider,["config unreadable"],[]))
            continue
        results.append(ASSESSORS[provider](cfg))

    if any(r["status"]=="INVALID_HOLD" for r in results):
        overall="INVALID_HOLD"
    elif any(r["status"]=="IMPLEMENTATION_REQUIRED" for r in results):
        overall="IMPLEMENTATION_REQUIRED"
    else:
        overall="BLOCKED_SAFE"

    return {
        "status":overall,
        "provider_count":len(results),
        "network_request_permitted":False,
        "providers":results,
    }
