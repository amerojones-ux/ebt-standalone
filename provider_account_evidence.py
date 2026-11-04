"""Redacted account-evidence registry for unresolved provider routing.

This module contains no credentials and performs no network access. It exists
to keep account existence, product hints, verified subscription facts, and
provider-documentation conflicts separate.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REGISTRY_PATH=ROOT/"config/provider_account_evidence.json"

EXPECTED={"SportsDataIO","Sportradar","RapidAPI"}
FORBIDDEN_FIELD_FRAGMENTS=("secret","password","token","api_key","apikey","email","account_id","credential")

def load_registry(path=REGISTRY_PATH):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)

def _field_names(obj):
    if isinstance(obj,dict):
        out=[]
        for k,v in obj.items():
            out.append(str(k).lower())
            out.extend(_field_names(v))
        return out
    if isinstance(obj,list):
        out=[]
        for item in obj:
            out.extend(_field_names(item))
        return out
    return []

def _provider_map(registry):
    return {p.get("name"):p for p in registry.get("providers",[]) if isinstance(p,dict)}

def validate_registry(registry):
    errors=[]
    if not isinstance(registry,dict):
        return ["registry must be object"]
    if registry.get("schema_version")!=1:
        errors.append("schema_version must be 1")
    providers=registry.get("providers")
    if not isinstance(providers,list):
        return errors+["providers must be list"]
    names=[p.get("name") for p in providers if isinstance(p,dict)]
    if set(names)!=EXPECTED or len(names)!=len(EXPECTED):
        errors.append("provider set mismatch")
    for field in _field_names(registry):
        if any(fragment in field for fragment in FORBIDDEN_FIELD_FRAGMENTS):
            errors.append("sensitive field forbidden in account evidence registry")
            break
    by=_provider_map(registry)

    sd=by.get("SportsDataIO",{})
    if sd.get("account_tier_verified") is True and sd.get("account_tier")!="FREE_TRIAL":
        errors.append("SportsDataIO verified tier mismatch")
    if sd.get("account_tier")=="FREE_TRIAL" and sd.get("model_evidence_allowed") is not False:
        errors.append("SportsDataIO Free Trial cannot be model evidence")
    if sd.get("provider_docs_scope_status")=="CONFLICTING" and sd.get("live_request_permitted") is True:
        errors.append("SportsDataIO conflicting scope cannot permit live request")
    if sd.get("product_hint_entitlement_proof") is not False:
        errors.append("SportsDataIO product hint cannot establish entitlement")

    sp=by.get("Sportradar",{})
    if sp.get("account_exists") is True and sp.get("exact_product_verified") is not True:
        if sp.get("live_request_permitted") is True:
            errors.append("Sportradar account existence cannot permit live request")
    if sp.get("exact_product_verified") is True and sp.get("access_level_verified") is not True:
        errors.append("Sportradar product verification requires access-level verification")
    if sp.get("live_request_permitted") is True:
        for field in ("exact_product_verified","access_level_verified","quota_verified"):
            if sp.get(field) is not True:
                errors.append("Sportradar live request missing "+field)

    ra=by.get("RapidAPI",{})
    if ra.get("account_exists") is True and ra.get("subscription_inventory_verified") is not True:
        if ra.get("live_request_permitted") is True:
            errors.append("RapidAPI sign-in cannot permit live request")
    if ra.get("live_request_permitted") is True:
        for field in (
            "subscription_inventory_verified","exact_product_verified",
            "exact_host_verified","exact_plan_verified","billing_object_verified",
            "quota_verified","overage_verified","exact_endpoint_verified",
        ):
            if ra.get(field) is not True:
                errors.append("RapidAPI live request missing "+field)
    if ra.get("product_hint_entitlement_proof") is not False:
        errors.append("RapidAPI ambiguous product hint cannot establish entitlement")

    for provider in providers:
        if not isinstance(provider,dict):
            continue
        if provider.get("model_evidence_allowed") is not False:
            errors.append(provider.get("name","unknown")+" model evidence must remain disabled")
    return errors

def evidence_for(provider,registry=None):
    if registry is None:
        registry=load_registry()
    return _provider_map(registry).get(provider)

def gap_report(registry=None):
    if registry is None:
        registry=load_registry()
    errors=validate_registry(registry)
    by=_provider_map(registry)
    gaps={}

    sd=by["SportsDataIO"]
    sd_gaps=[]
    if sd.get("provider_docs_scope_status")!="RECONCILED":
        sd_gaps.append("official/account scope conflict unresolved")
    if sd.get("exact_product_verified") is not True:
        sd_gaps.append("exact subscribed product not verified")
    if sd.get("exact_feed_verified") is not True:
        sd_gaps.append("exact feed/endpoint scope not verified")
    if sd.get("quota_verified") is not True:
        sd_gaps.append("quota not verified")
    if sd.get("overage_verified") is not True:
        sd_gaps.append("overage behavior not verified")
    gaps["SportsDataIO"]=sd_gaps

    sp=by["Sportradar"]
    sp_gaps=[]
    if sp.get("exact_product_verified") is not True:
        sp_gaps.append("NFL product/package not verified")
    if sp.get("access_level_verified") is not True:
        sp_gaps.append("trial/production access level not verified")
    if sp.get("quota_verified") is not True:
        sp_gaps.append("quota/QPS not verified")
    gaps["Sportradar"]=sp_gaps

    ra=by["RapidAPI"]
    ra_gaps=[]
    checks=(
        ("subscription_inventory_verified","subscription inventory not verified"),
        ("exact_product_verified","exact API product not verified"),
        ("exact_host_verified","X-RapidAPI-Host not verified"),
        ("exact_plan_verified","subscription plan not verified"),
        ("billing_object_verified","billing object not verified"),
        ("quota_verified","quota not verified"),
        ("overage_verified","overage behavior not verified"),
        ("exact_endpoint_verified","endpoint not verified"),
    )
    for field,label in checks:
        if ra.get(field) is not True:
            ra_gaps.append(label)
    gaps["RapidAPI"]=ra_gaps

    return {
        "status":"INVALID_HOLD" if errors else "ACCOUNT_EVIDENCE_HOLD",
        "errors":errors,
        "gaps":gaps,
        "live_request_permitted":False,
        "model_evidence_allowed":False,
    }
