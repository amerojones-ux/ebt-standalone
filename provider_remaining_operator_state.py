"""Deterministic operator-state engine for unresolved provider integrations.

Reads only committed, redacted repository state. It never reads secrets,
contacts providers, authorizes requests, or enables forecasting.
"""
import json
import urllib.parse
from pathlib import Path

from provider_account_evidence import load_registry, validate_registry
from provider_account_evidence_consistency import (
    CONFIGS as CONSISTENCY_CONFIGS,
    validate_consistency,
)
from provider_account_metadata_transition import load_configs

ROOT=Path(__file__).resolve().parent

REMAINING=("SportsDataIO","Sportradar","RapidAPI")
READINESS_PATH=ROOT/"config/provider_readiness.json"

METADATA_WORKFLOWS={
    "SportsDataIO":".github/workflows/sportsdataio-account-metadata-review.yml",
    "Sportradar":".github/workflows/sportradar-account-metadata-review.yml",
    "RapidAPI":".github/workflows/rapidapi-account-metadata-review.yml",
}
PROBE_WORKFLOWS={
    "SportsDataIO":".github/workflows/sportsdataio-live-probe.yml",
    "Sportradar":".github/workflows/sportradar-nfl-live-probe.yml",
    "RapidAPI":".github/workflows/rapidapi-live-probe.yml",
}

BLOCKED_ACTIONS=[
    "provider_network_request",
    "live_auth_promotion",
    "forecast_activation",
    "model_evidence_activation",
    "network_autorun",
]

def _load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)

def _readiness_record(readiness,name):
    for row in readiness.get("providers",[]):
        if isinstance(row,dict) and row.get("name")==name:
            return row
    return None

def _account_record(registry,name):
    for row in registry.get("providers",[]):
        if isinstance(row,dict) and row.get("name")==name:
            return row
    return None

def _flag_missing(obj, requirements):
    missing=[]
    for key,expected in requirements.items():
        if obj.get(key)!=expected:
            missing.append(key)
    return missing

def _sportsdataio_missing(account,cfg):
    missing=[]
    missing += ["account."+x for x in _flag_missing(account,{
        "provider_docs_scope_status":"RECONCILED",
        "exact_product_verified":True,
        "exact_feed_verified":True,
        "quota_verified":True,
        "overage_verified":True,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    })]
    missing += ["config."+x for x in _flag_missing(cfg,{
        "trial_scope_reconciled":True,
        "official_scope_status":"RECONCILED",
        "quota_reviewed":True,
        "overage_reviewed":True,
        "network_enabled":False,
        "forecast_enabled":False,
        "model_evidence_allowed":False,
    })]
    if not isinstance(cfg.get("probe_product"),str) or not cfg["probe_product"].strip():
        missing.append("config.probe_product")
    endpoint=cfg.get("probe_endpoint")
    if not isinstance(endpoint,str) or not endpoint.startswith("https://api.sportsdata.io/v3/"):
        missing.append("config.probe_endpoint")
    return sorted(set(missing))

def _sportradar_missing(account,cfg):
    missing=[]
    missing += ["account."+x for x in _flag_missing(account,{
        "account_tier_verified":True,
        "subscription_details_verified":True,
        "product_inventory_verified":True,
        "exact_product_verified":True,
        "access_level_verified":True,
        "quota_verified":True,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    })]
    missing += ["config."+x for x in _flag_missing(cfg,{
        "product_verified":True,
        "subscription_details_verified":True,
        "product_inventory_verified":True,
        "access_level_verified":True,
        "quota_reviewed":True,
        "network_enabled":False,
        "quota_impact_approved":False,
        "request_count":0,
        "forecast_enabled":False,
    })]
    access=cfg.get("access_level")
    if access not in {"trial","production"}:
        missing.append("config.access_level")
    if not isinstance(cfg.get("product_name"),str) or not cfg["product_name"].strip():
        missing.append("config.product_name")
    expected=(
        "https://api.sportradar.com/nfl/official/"
        +str(access)+"/v7/en/league/hierarchy.json"
    )
    if cfg.get("probe_endpoint")!=expected:
        missing.append("config.probe_endpoint")
    return sorted(set(missing))

def _rapidapi_missing(account,cfg):
    missing=[]
    missing += ["account."+x for x in _flag_missing(account,{
        "account_tier_verified":True,
        "subscription_inventory_verified":True,
        "subscription_verified":True,
        "route_binding_verified":True,
        "exact_product_verified":True,
        "exact_host_verified":True,
        "exact_plan_verified":True,
        "billing_object_verified":True,
        "quota_verified":True,
        "overage_verified":True,
        "exact_endpoint_verified":True,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    })]
    missing += ["config."+x for x in _flag_missing(cfg,{
        "subscription_inventory_verified":True,
        "subscription_verified":True,
        "route_binding_verified":True,
        "quota_reviewed":True,
        "overage_reviewed":True,
        "endpoint_reviewed":True,
        "network_enabled":False,
        "request_count":0,
        "forecast_enabled":False,
    })]
    for key in ("api_product","rapidapi_host","plan_name","billing_object","probe_endpoint"):
        if not isinstance(cfg.get(key),str) or not cfg[key].strip():
            missing.append("config."+key)
    if cfg.get("pricing_type") in {None,"","UNKNOWN"}:
        missing.append("config.pricing_type")
    endpoint=cfg.get("probe_endpoint")
    host=cfg.get("rapidapi_host")
    if isinstance(endpoint,str) and endpoint:
        parsed=urllib.parse.urlsplit(endpoint)
        if (
            parsed.scheme!="https" or parsed.hostname!=host or parsed.query
            or parsed.fragment or parsed.username is not None
            or parsed.password is not None or parsed.port is not None
        ):
            missing.append("config.probe_endpoint")
    return sorted(set(missing))

MISSING_BUILDERS={
    "SportsDataIO":_sportsdataio_missing,
    "Sportradar":_sportradar_missing,
    "RapidAPI":_rapidapi_missing,
}

def assess_remaining_provider_state(
    *,
    readiness=None,
    registry=None,
    configs=None,
    path_exists=None,
):
    if readiness is None:
        readiness=_load_json(READINESS_PATH)
    if registry is None:
        registry=load_registry()
    if configs is None:
        configs=load_configs()
    if path_exists is None:
        path_exists=lambda rel:(ROOT/rel).is_file()

    errors=[]
    if validate_registry(registry):
        errors.extend("account_registry:"+x for x in validate_registry(registry))
    path_map={CONSISTENCY_CONFIGS[name]:cfg for name,cfg in configs.items()}
    consistency=validate_consistency(
        registry=registry,
        config_loader=lambda path:path_map[path],
    )
    errors.extend("consistency:"+x for x in consistency)

    if readiness.get("forecast_enabled") is not False:
        errors.append("global forecast_enabled must remain false")
    if readiness.get("network_autorun_enabled") is not False:
        errors.append("global network_autorun_enabled must remain false")

    providers=[]
    for name in REMAINING:
        r=_readiness_record(readiness,name)
        a=_account_record(registry,name)
        cfg=configs.get(name)
        if r is None or a is None or not isinstance(cfg,dict):
            providers.append({
                "provider":name,
                "status":"INVALID_HOLD",
                "errors":["required committed state missing"],
                "next_stage":"REPAIR_REPOSITORY_STATE",
                "next_workflow":None,
                "missing_metadata":[],
                "probe_workflow_present":bool(path_exists(PROBE_WORKFLOWS[name])),
                "blocked_actions":list(BLOCKED_ACTIONS),
            })
            continue

        local_errors=[]
        if r.get("contract_ready") is not True:
            local_errors.append("provider contract not ready")
        if r.get("entitlement_verified") is not False:
            local_errors.append("entitlement_verified unexpectedly true")
        if r.get("identity_verified") is not False:
            local_errors.append("identity_verified unexpectedly true")
        if r.get("freshness_verified") is not False:
            local_errors.append("freshness_verified unexpectedly true")
        if r.get("model_evidence_allowed") is not False:
            local_errors.append("readiness model_evidence_allowed unexpectedly true")
        if a.get("live_request_permitted") is not False:
            local_errors.append("account live_request_permitted unexpectedly true")
        if a.get("model_evidence_allowed") is not False:
            local_errors.append("account model_evidence_allowed unexpectedly true")
        if cfg.get("network_enabled") is not False:
            local_errors.append("provider config network_enabled unexpectedly true")
        if cfg.get("forecast_enabled") is not False:
            local_errors.append("provider config forecast_enabled unexpectedly true")

        missing=MISSING_BUILDERS[name](a,cfg)
        probe_present=bool(path_exists(PROBE_WORKFLOWS[name]))
        metadata_workflow_present=bool(path_exists(METADATA_WORKFLOWS[name]))

        if local_errors:
            status="INVALID_HOLD"
            next_stage="REPAIR_REPOSITORY_STATE"
            next_workflow=None
        elif r.get("live_auth_verified") is True:
            status="LIVE_AUTH_VERIFIED"
            next_stage="ENTITLEMENT_IDENTITY_FRESHNESS_EVIDENCE"
            next_workflow=None
        elif missing:
            status="ACCOUNT_METADATA_REQUIRED"
            next_stage="SIGNED_ACCOUNT_METADATA_CLAIM"
            next_workflow=METADATA_WORKFLOWS[name]
            if not metadata_workflow_present:
                status="INVALID_HOLD"
                local_errors.append("metadata claim workflow missing")
                next_stage="REPAIR_REPOSITORY_STATE"
                next_workflow=None
        elif not probe_present:
            status="METADATA_PERSISTED_PROBE_ENGINEERING_REQUIRED"
            next_stage="HARDENED_ONE_SHOT_PROBE_ENGINEERING"
            next_workflow=None
        else:
            status="PROBE_PREPARED_AWAITING_EXPLICIT_AUTHORIZATION"
            next_stage="EXPLICIT_ONE_SHOT_REQUEST_AUTHORIZATION"
            next_workflow=PROBE_WORKFLOWS[name]

        providers.append({
            "provider":name,
            "status":status,
            "errors":local_errors,
            "next_stage":next_stage,
            "next_workflow":next_workflow,
            "metadata_claim_workflow":METADATA_WORKFLOWS[name],
            "probe_workflow":PROBE_WORKFLOWS[name],
            "missing_metadata":missing,
            "probe_workflow_present":probe_present,
            "blocked_actions":list(BLOCKED_ACTIONS) if r.get("live_auth_verified") is not True else [
                "forecast_activation","model_evidence_activation","network_autorun"
            ],
        })

    if errors or any(p["status"]=="INVALID_HOLD" for p in providers):
        status="INVALID_HOLD"
    elif all(p["status"]=="LIVE_AUTH_VERIFIED" for p in providers):
        status="REMAINING_LIVE_AUTH_COMPLETE_SAFE_HOLD"
    else:
        status="SAFE_HOLD"

    readiness_rows=[
        row for row in readiness.get("providers",[]) if isinstance(row,dict)
    ]
    overall_live_auth=sum(
        1 for row in readiness_rows if row.get("live_auth_verified") is True
    )
    return {
        "schema_version":1,
        "status":status,
        "forecast_enabled":False,
        "network_autorun_enabled":False,
        "overall_provider_count":len(readiness_rows),
        "overall_live_auth_verified_count":overall_live_auth,
        "remaining_provider_count":len(providers),
        "remaining_live_auth_verified_count":sum(
            1 for p in providers if p["status"]=="LIVE_AUTH_VERIFIED"
        ),
        "errors":errors,
        "providers":providers,
    }
