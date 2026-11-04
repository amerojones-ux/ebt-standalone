"""Non-mutating provider account-metadata transition preview.

Consumes verified nonsecret account/support facts and proposes synchronized
updates to the redacted account-evidence registry and operational provider
configs. It never reads credentials, performs network I/O, writes files, or
permits forecast/provider execution.
"""
import copy
import json
import re
import urllib.parse
from pathlib import Path

from provider_account_evidence import load_registry, validate_registry
from rapidapi_routing_contract import HOST, PRICING_TYPES, AMBIGUOUS_PRODUCT_NAMES

ROOT=Path(__file__).resolve().parent

CONFIG_PATHS={
    "SportsDataIO":"config/sportsdataio_access.json",
    "Sportradar":"config/sportradar_nfl_auth.json",
    "RapidAPI":"config/rapidapi_routing.json",
}
ALLOWED_SOURCE_TYPES={"ACCOUNT_PORTAL","PROVIDER_SUPPORT"}
SAFE_TEXT=re.compile(r"^[A-Za-z0-9 ._+()&/-]{1,160}$")
FORBIDDEN_VALUE_FRAGMENTS=("apikey","api_key","secret","token","password","bearer","authorization")

def _load_json(path):
    with (ROOT/path).open(encoding="utf-8") as handle:
        return json.load(handle)

def load_configs():
    return {provider:_load_json(path) for provider,path in CONFIG_PATHS.items()}

def _clean_text(value,label):
    if not isinstance(value,str):
        raise ValueError(label+" must be string")
    value=value.strip()
    if not value or not SAFE_TEXT.fullmatch(value):
        raise ValueError(label+" contains unsafe or unsupported characters")
    lowered=value.casefold()
    if any(fragment in lowered for fragment in FORBIDDEN_VALUE_FRAGMENTS):
        raise ValueError(label+" resembles credential material")
    return value

def _https_endpoint(value,expected_host=None):
    if not isinstance(value,str) or not value:
        raise ValueError("endpoint required")
    parsed=urllib.parse.urlsplit(value)
    if parsed.scheme!="https":
        raise ValueError("endpoint must use https")
    if not parsed.hostname:
        raise ValueError("endpoint host required")
    if expected_host is not None and parsed.hostname!=expected_host:
        raise ValueError("endpoint host mismatch")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("endpoint userinfo forbidden")
    if parsed.port is not None:
        raise ValueError("endpoint explicit port forbidden")
    if parsed.query or parsed.fragment:
        raise ValueError("endpoint query/fragment forbidden")
    return value

def _base_result(provider,errors=None):
    errors=[] if errors is None else list(errors)
    return {
        "provider":provider,
        "status":"HOLD" if errors else "VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW",
        "errors":errors,
        "write_permitted":False,
        "network_request_permitted":False,
        "forecast_activation_permitted":False,
        "model_evidence_allowed":False,
    }

def _validate_source(facts):
    source=facts.get("source_type")
    if source not in ALLOWED_SOURCE_TYPES:
        raise ValueError("source_type must be ACCOUNT_PORTAL or PROVIDER_SUPPORT")
    return source

def _exact_keys(facts,allowed):
    extra=set(facts)-set(allowed)
    if extra:
        raise ValueError("unsupported fact fields: "+",".join(sorted(extra)))

def _sportsdataio(facts,registry,configs):
    _exact_keys(facts,{
        "source_type","scope_status","product_name","feed_scope",
        "endpoint","quota_reviewed","overage_reviewed"
    })
    _validate_source(facts)
    if facts.get("scope_status")!="RECONCILED":
        raise ValueError("SportsDataIO scope must be explicitly reconciled")
    product=_clean_text(facts.get("product_name"),"product_name")
    feed=_clean_text(facts.get("feed_scope"),"feed_scope")
    endpoint=_https_endpoint(facts.get("endpoint"),"api.sportsdata.io")
    if not urllib.parse.urlsplit(endpoint).path.startswith("/v3/"):
        raise ValueError("SportsDataIO endpoint must be v3")
    if facts.get("quota_reviewed") is not True:
        raise ValueError("SportsDataIO quota must be reviewed")
    if facts.get("overage_reviewed") is not True:
        raise ValueError("SportsDataIO overage behavior must be reviewed")

    out_registry=copy.deepcopy(registry)
    out_configs=copy.deepcopy(configs)
    rec=next(p for p in out_registry["providers"] if p["name"]=="SportsDataIO")
    rec.update({
        "provider_docs_scope_status":"RECONCILED",
        "exact_product_verified":True,
        "exact_feed_verified":True,
        "quota_verified":True,
        "overage_verified":True,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    })
    cfg=out_configs["SportsDataIO"]
    cfg.update({
        "probe_product":product+" / "+feed,
        "probe_endpoint":endpoint,
        "trial_scope_reconciled":True,
        "official_scope_status":"RECONCILED",
        "quota_reviewed":True,
        "overage_reviewed":True,
        "network_enabled":False,
        "forecast_enabled":False,
        "model_evidence_allowed":False,
    })
    return out_registry,out_configs

def _sportradar(facts,registry,configs):
    _exact_keys(facts,{
        "source_type","product_name","package_name","access_level",
        "quota_reviewed"
    })
    _validate_source(facts)
    product=_clean_text(facts.get("product_name"),"product_name")
    package=_clean_text(facts.get("package_name"),"package_name")
    if "nfl" not in product.casefold():
        raise ValueError("Sportradar product must explicitly identify NFL")
    access=facts.get("access_level")
    if access not in {"trial","production"}:
        raise ValueError("Sportradar access_level must be trial or production")
    if facts.get("quota_reviewed") is not True:
        raise ValueError("Sportradar quota/QPS must be reviewed")
    endpoint=(
        "https://api.sportradar.com/nfl/official/"
        +access+
        "/v7/en/league/hierarchy.json"
    )

    out_registry=copy.deepcopy(registry)
    out_configs=copy.deepcopy(configs)
    rec=next(p for p in out_registry["providers"] if p["name"]=="Sportradar")
    rec.update({
        "account_tier":access,
        "account_tier_verified":True,
        "account_product_hint":product+" / "+package,
        "subscription_details_verified":True,
        "product_inventory_verified":True,
        "exact_product_verified":True,
        "access_level_verified":True,
        "quota_verified":True,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    })
    cfg=out_configs["Sportradar"]
    cfg.update({
        "access_level":access,
        "product_name":product+" / "+package,
        "product_verified":True,
        "subscription_details_verified":True,
        "product_inventory_verified":True,
        "access_level_verified":True,
        "quota_reviewed":True,
        "probe_endpoint":endpoint,
        "network_enabled":False,
        "quota_impact_approved":False,
        "request_count":0,
        "forecast_enabled":False,
    })
    return out_registry,out_configs

def _rapidapi(facts,registry,configs):
    _exact_keys(facts,{
        "source_type","product_name","host","pricing_type","plan_name",
        "billing_object","endpoint","quota_reviewed","overage_reviewed"
    })
    _validate_source(facts)
    product=_clean_text(facts.get("product_name"),"product_name")
    if product.casefold() in AMBIGUOUS_PRODUCT_NAMES:
        raise ValueError("RapidAPI exact product required; ambiguous name rejected")
    host=facts.get("host")
    if not isinstance(host,str) or not HOST.fullmatch(host) or "." not in host:
        raise ValueError("RapidAPI exact host required")
    pricing=facts.get("pricing_type")
    if pricing not in PRICING_TYPES or pricing=="UNKNOWN":
        raise ValueError("RapidAPI pricing type must be reviewed")
    plan=_clean_text(facts.get("plan_name"),"plan_name")
    billing=_clean_text(facts.get("billing_object"),"billing_object")
    endpoint=_https_endpoint(facts.get("endpoint"),host)
    if facts.get("quota_reviewed") is not True:
        raise ValueError("RapidAPI quota must be reviewed")
    if facts.get("overage_reviewed") is not True:
        raise ValueError("RapidAPI overage behavior must be reviewed")

    out_registry=copy.deepcopy(registry)
    out_configs=copy.deepcopy(configs)
    rec=next(p for p in out_registry["providers"] if p["name"]=="RapidAPI")
    rec.update({
        "account_tier":pricing,
        "account_tier_verified":True,
        "account_product_hint":product,
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
    })
    cfg=out_configs["RapidAPI"]
    cfg.update({
        "api_product":product,
        "rapidapi_host":host,
        "pricing_type":pricing,
        "plan_name":plan,
        "billing_object":billing,
        "subscription_inventory_verified":True,
        "subscription_verified":True,
        "route_binding_verified":True,
        "quota_reviewed":True,
        "overage_reviewed":True,
        "endpoint_reviewed":True,
        "network_enabled":False,
        "request_count":0,
        "forecast_enabled":False,
    })
    cfg["reviewed_probe_endpoint"]=endpoint
    return out_registry,out_configs

BUILDERS={
    "SportsDataIO":_sportsdataio,
    "Sportradar":_sportradar,
    "RapidAPI":_rapidapi,
}

def build_transition(provider,facts,*,registry=None,configs=None):
    if provider not in BUILDERS:
        result=_base_result(str(provider),["unsupported provider"])
        return result
    if not isinstance(facts,dict):
        return _base_result(provider,["facts must be object"])
    if registry is None:
        registry=load_registry()
    if configs is None:
        configs=load_configs()
    registry_errors=validate_registry(registry)
    if registry_errors:
        return _base_result(provider,registry_errors)
    try:
        next_registry,next_configs=BUILDERS[provider](facts,registry,configs)
    except ValueError as exc:
        return _base_result(provider,[str(exc)])
    errors=validate_registry(next_registry)
    result=_base_result(provider,errors)
    if errors:
        return result
    result["candidate_registry"]=next_registry
    result["candidate_configs"]=next_configs
    result["source_type"]=facts.get("source_type")
    return result
