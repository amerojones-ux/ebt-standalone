"""Controlled apply manifest for source-verified provider account metadata.

The apply may write only an isolated branch. It never authorizes a provider
request, forecasting, or model evidence.
"""
import hashlib
import hmac
import json

from provider_account_evidence import validate_registry
from provider_account_evidence_consistency import validate_consistency, CONFIGS as CONSISTENCY_CONFIGS
from provider_account_metadata_promotion_preview import (
    build_metadata_promotion_preview,
    verify_metadata_promotion_preview,
)
from provider_account_metadata_transition import CONFIG_PATHS, load_configs
from provider_account_evidence import load_registry

PROVIDER_CONFIG_PATHS={
    "SportsDataIO":"config/sportsdataio_access.json",
    "Sportradar":"config/sportradar_nfl_auth.json",
    "RapidAPI":"config/rapidapi_routing.json",
}

BODY_FIELDS={
    "schema_version","apply_type","apply_status","provider",
    "promotion_preview_run_id","promotion_preview_commit","promotion_preview_sha256",
    "source_review_run_id","source_claim_run_id","current_state_sha256",
    "target_account_evidence_path","target_provider_config_path",
    "candidate_registry","candidate_provider_config",
    "account_evidence_file_sha256","provider_config_file_sha256",
    "isolated_branch_write_permitted","main_write_permitted",
    "provider_network_request_permitted","forecast_activation_permitted",
    "model_evidence_allowed",
}
ALL_FIELDS=BODY_FIELDS|{"apply_sha256"}

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()

def _file_bytes(value):
    return (json.dumps(value,indent=2,sort_keys=True)+"\n").encode("utf-8")

def _provider_entry(registry,name):
    for entry in registry.get("providers",[]):
        if isinstance(entry,dict) and entry.get("name")==name:
            return entry
    return None

def build_metadata_promotion_apply(
    claim,
    decision,
    signed_preview,
    *,
    promotion_preview_run_id,
    promotion_preview_commit,
    registry=None,
    configs=None,
):
    if not verify_metadata_promotion_preview(signed_preview):
        raise ValueError("signed promotion preview invalid")
    if not isinstance(promotion_preview_run_id,str) or not promotion_preview_run_id.isdigit():
        raise ValueError("promotion preview run id invalid")
    if not isinstance(promotion_preview_commit,str) or len(promotion_preview_commit)!=40:
        raise ValueError("promotion preview commit invalid")
    if registry is None:
        registry=load_registry()
    if configs is None:
        configs=load_configs()

    rebuilt=build_metadata_promotion_preview(
        claim,
        decision,
        source_review_run_id=signed_preview["source_review_run_id"],
        source_review_commit=signed_preview["source_review_commit"],
        registry=registry,
        configs=configs,
    )
    if rebuilt!=signed_preview:
        raise ValueError("signed promotion preview drifted from current main state")

    provider=signed_preview["provider"]
    candidate_registry=signed_preview["candidate_registry"]
    candidate_configs=signed_preview["candidate_configs"]
    if validate_registry(candidate_registry):
        raise ValueError("candidate account evidence registry invalid")
    path_map={
        CONSISTENCY_CONFIGS[name]:cfg
        for name,cfg in candidate_configs.items()
    }
    if validate_consistency(
        registry=candidate_registry,
        config_loader=lambda path:path_map[path],
    ):
        raise ValueError("candidate account/config consistency invalid")

    if set(candidate_configs)!=set(configs):
        raise ValueError("candidate config provider set mismatch")

    for name in configs:
        if name!=provider and candidate_configs[name]!=configs[name]:
            raise ValueError("cross-provider config mutation forbidden")

    current_target=_provider_entry(registry,provider)
    candidate_target=_provider_entry(candidate_registry,provider)
    if current_target is None or candidate_target is None:
        raise ValueError("target account evidence entry missing")

    current_other=[x for x in registry["providers"] if x.get("name")!=provider]
    candidate_other=[x for x in candidate_registry["providers"] if x.get("name")!=provider]
    if current_other!=candidate_other:
        raise ValueError("cross-provider account evidence mutation forbidden")

    if candidate_target==current_target and candidate_configs[provider]==configs[provider]:
        raise ValueError("metadata promotion is no-op/already applied")

    if candidate_target.get("live_request_permitted") is not False:
        raise ValueError("live request unexpectedly permitted")
    if candidate_target.get("model_evidence_allowed") is not False:
        raise ValueError("model evidence unexpectedly permitted")
    target_cfg=candidate_configs[provider]
    if target_cfg.get("network_enabled") is not False:
        raise ValueError("provider network unexpectedly enabled")
    if target_cfg.get("forecast_enabled") is not False:
        raise ValueError("forecast unexpectedly enabled")

    body={
        "schema_version":1,
        "apply_type":"ACCOUNT_METADATA_PROMOTION_APPLY",
        "apply_status":"VALID_ACCOUNT_METADATA_PROMOTION_APPLY",
        "provider":provider,
        "promotion_preview_run_id":promotion_preview_run_id,
        "promotion_preview_commit":promotion_preview_commit.lower(),
        "promotion_preview_sha256":signed_preview["preview_sha256"],
        "source_review_run_id":signed_preview["source_review_run_id"],
        "source_claim_run_id":signed_preview["source_claim_run_id"],
        "current_state_sha256":signed_preview["current_state_sha256"],
        "target_account_evidence_path":"config/provider_account_evidence.json",
        "target_provider_config_path":PROVIDER_CONFIG_PATHS[provider],
        "candidate_registry":candidate_registry,
        "candidate_provider_config":target_cfg,
        "account_evidence_file_sha256":hashlib.sha256(_file_bytes(candidate_registry)).hexdigest(),
        "provider_config_file_sha256":hashlib.sha256(_file_bytes(target_cfg)).hexdigest(),
        "isolated_branch_write_permitted":True,
        "main_write_permitted":False,
        "provider_network_request_permitted":False,
        "forecast_activation_permitted":False,
        "model_evidence_allowed":False,
    }
    result=dict(body)
    result["apply_sha256"]=_sha(body)
    return result

def verify_metadata_promotion_apply(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    if value.get("schema_version")!=1:
        return False
    if value.get("apply_type")!="ACCOUNT_METADATA_PROMOTION_APPLY":
        return False
    if value.get("apply_status")!="VALID_ACCOUNT_METADATA_PROMOTION_APPLY":
        return False
    provider=value.get("provider")
    if provider not in PROVIDER_CONFIG_PATHS:
        return False
    for key in ("promotion_preview_run_id","source_review_run_id","source_claim_run_id"):
        val=value.get(key)
        if not isinstance(val,str) or not val.isdigit():
            return False
    if not isinstance(value.get("promotion_preview_commit"),str) or len(value["promotion_preview_commit"])!=40:
        return False
    for key in (
        "promotion_preview_sha256","current_state_sha256",
        "account_evidence_file_sha256","provider_config_file_sha256","apply_sha256",
    ):
        val=value.get(key)
        if not isinstance(val,str) or len(val)!=64:
            return False
    if value.get("target_account_evidence_path")!="config/provider_account_evidence.json":
        return False
    if value.get("target_provider_config_path")!=PROVIDER_CONFIG_PATHS[provider]:
        return False
    if not isinstance(value.get("candidate_registry"),dict):
        return False
    if not isinstance(value.get("candidate_provider_config"),dict):
        return False
    if value.get("isolated_branch_write_permitted") is not True:
        return False
    for key in (
        "main_write_permitted","provider_network_request_permitted",
        "forecast_activation_permitted","model_evidence_allowed",
    ):
        if value.get(key) is not False:
            return False
    body={k:value[k] for k in BODY_FIELDS}
    return hmac.compare_digest(_sha(body),value["apply_sha256"])
