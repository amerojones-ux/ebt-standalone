"""Cross-check operational provider configs against redacted account evidence.

No network access and no credentials. This prevents an operational config from
claiming verified product/plan/route facts that are absent from the separate
account-evidence registry.
"""
import json
from pathlib import Path

from provider_account_evidence import evidence_for, load_registry, validate_registry

ROOT=Path(__file__).resolve().parent

CONFIGS={
    "SportsDataIO":"config/sportsdataio_access.json",
    "Sportradar":"config/sportradar_nfl_auth.json",
    "RapidAPI":"config/rapidapi_routing.json",
}

def _load_json(path):
    with (ROOT/path).open(encoding="utf-8") as handle:
        return json.load(handle)

def validate_consistency(*,registry=None,config_loader=_load_json):
    if registry is None:
        registry=load_registry()
    errors=list(validate_registry(registry))
    for provider,path in CONFIGS.items():
        try:
            cfg=config_loader(path)
        except Exception:
            errors.append(provider+" config unreadable")
            continue
        account=evidence_for(provider,registry)
        if not isinstance(account,dict):
            errors.append(provider+" account evidence missing")
            continue

        if provider=="SportsDataIO":
            if cfg.get("account_access_confirmed") is True and account.get("account_exists") is not True:
                errors.append("SportsDataIO account confirmation unsupported")
            if account.get("account_tier_verified") is True:
                if account.get("account_tier")=="FREE_TRIAL" and cfg.get("declared_access_method")!="FREE_TRIAL":
                    errors.append("SportsDataIO access method contradicts account tier")
            if cfg.get("trial_scope_reconciled") is True and account.get("provider_docs_scope_status")!="RECONCILED":
                errors.append("SportsDataIO scope reconciliation unsupported")
            if cfg.get("quota_reviewed") is True and account.get("quota_verified") is not True:
                errors.append("SportsDataIO quota review unsupported")
            if cfg.get("overage_reviewed") is True and account.get("overage_verified") is not True:
                errors.append("SportsDataIO overage review unsupported")
            if isinstance(cfg.get("probe_product"),str) and cfg.get("probe_product").strip():
                if account.get("exact_product_verified") is not True:
                    errors.append("SportsDataIO product scope unsupported")
            if isinstance(cfg.get("probe_endpoint"),str) and cfg.get("probe_endpoint").strip():
                if account.get("exact_feed_verified") is not True:
                    errors.append("SportsDataIO endpoint scope unsupported")

        elif provider=="Sportradar":
            pairs=(
                ("subscription_details_verified","subscription_details_verified"),
                ("product_inventory_verified","product_inventory_verified"),
                ("access_level_verified","access_level_verified"),
                ("product_verified","exact_product_verified"),
                ("quota_reviewed","quota_verified"),
            )
            if cfg.get("account_registration_confirmed") is True and account.get("account_exists") is not True:
                errors.append("Sportradar account registration unsupported")
            for cfg_field,evidence_field in pairs:
                if cfg.get(cfg_field) is True and account.get(evidence_field) is not True:
                    errors.append("Sportradar "+cfg_field+" unsupported")
            if isinstance(cfg.get("product_name"),str) and cfg.get("product_name").strip():
                if account.get("exact_product_verified") is not True:
                    errors.append("Sportradar product name unsupported")
            if cfg.get("access_level") in {"trial","production"}:
                if account.get("access_level_verified") is not True:
                    errors.append("Sportradar access level unsupported")

        elif provider=="RapidAPI":
            pairs=(
                ("subscription_inventory_verified","subscription_inventory_verified"),
                ("route_binding_verified","route_binding_verified"),
                ("subscription_verified","subscription_verified"),
                ("quota_reviewed","quota_verified"),
                ("overage_reviewed","overage_verified"),
                ("endpoint_reviewed","exact_endpoint_verified"),
            )
            if cfg.get("account_signin_confirmed") is True and account.get("account_exists") is not True:
                errors.append("RapidAPI sign-in unsupported")
            for cfg_field,evidence_field in pairs:
                if cfg.get(cfg_field) is True and account.get(evidence_field) is not True:
                    errors.append("RapidAPI "+cfg_field+" unsupported")
            if isinstance(cfg.get("api_product"),str) and cfg.get("api_product").strip():
                if account.get("exact_product_verified") is not True:
                    errors.append("RapidAPI product name unsupported")
            if isinstance(cfg.get("rapidapi_host"),str) and cfg.get("rapidapi_host").strip():
                if account.get("exact_host_verified") is not True:
                    errors.append("RapidAPI host unsupported")
            if isinstance(cfg.get("plan_name"),str) and cfg.get("plan_name").strip():
                if account.get("exact_plan_verified") is not True:
                    errors.append("RapidAPI plan unsupported")
            if isinstance(cfg.get("billing_object"),str) and cfg.get("billing_object").strip():
                if account.get("billing_object_verified") is not True:
                    errors.append("RapidAPI billing object unsupported")
            if isinstance(cfg.get("probe_endpoint"),str) and cfg.get("probe_endpoint").strip():
                if account.get("exact_endpoint_verified") is not True:
                    errors.append("RapidAPI endpoint unsupported")
            if cfg.get("endpoint_reviewed") is True and not (
                isinstance(cfg.get("probe_endpoint"),str) and cfg.get("probe_endpoint").strip()
            ):
                errors.append("RapidAPI reviewed endpoint missing")

    return errors
