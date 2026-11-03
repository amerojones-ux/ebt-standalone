"""Build an exact, SAFE_HOLD live-auth promotion apply candidate.

This module never performs network requests, writes repository files, creates
branches, opens pull requests, or enables forecasting.
"""
import copy
import hashlib
import json

from provider_activation_gate import status, validate_config
from provider_live_auth_promotion_preview import build_live_auth_promotion_preview
from provider_readiness_evidence_gate import evidence_supports_readiness

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def build_live_auth_promotion_apply(
    readiness,
    ledger,
    verified_package,
    *,
    trusted_now,
):
    if not isinstance(verified_package,dict):
        raise ValueError("verified promotion package required")
    if (
        verified_package.get("package_status")
        !="VERIFIED_LIVE_AUTH_PROMOTION_PREVIEW_PACKAGE"
    ):
        raise ValueError("promotion package not verified")
    if verified_package.get("claim")!="live_auth_verified":
        raise ValueError("promotion package claim mismatch")

    signed_preview=verified_package.get("signed_preview")
    decision=verified_package.get("attested_review_decision")
    if not isinstance(signed_preview,dict) or not isinstance(decision,dict):
        raise ValueError("promotion package payload missing")

    fresh=build_live_auth_promotion_preview(
        readiness,
        ledger,
        decision,
        trusted_now=trusted_now,
    )
    if fresh.get("preview_sha256")!=signed_preview.get("preview_sha256"):
        raise ValueError("current config drifted from signed promotion preview")
    if fresh!=signed_preview:
        raise ValueError("signed promotion preview semantic mismatch")

    updated_readiness=copy.deepcopy(fresh["preview_readiness"])
    updated_ledger=copy.deepcopy(fresh["preview_ledger"])

    if validate_config(updated_readiness):
        raise ValueError("promoted readiness config invalid")
    evidence_errors=evidence_supports_readiness(
        updated_readiness,
        updated_ledger,
        trusted_now=trusted_now,
    )
    if evidence_errors:
        raise ValueError("promoted readiness lacks valid evidence")
    gate=status(updated_readiness,evidence_ok=True)
    if gate!="SAFE_HOLD":
        raise ValueError("promotion apply must remain SAFE_HOLD")
    if updated_readiness.get("forecast_enabled") is not False:
        raise ValueError("forecast activation forbidden")
    if updated_readiness.get("network_autorun_enabled") is not False:
        raise ValueError("network autorun activation forbidden")

    provider=fresh["provider"]
    before_target=next(
        (x for x in readiness["providers"] if x.get("name")==provider),
        None,
    )
    after_target=next(
        (x for x in updated_readiness["providers"] if x.get("name")==provider),
        None,
    )
    if before_target is None or after_target is None:
        raise ValueError("provider missing from readiness config")
    changed={
        key for key in set(before_target)|set(after_target)
        if before_target.get(key)!=after_target.get(key)
    }
    if changed!={"live_auth_verified"}:
        raise ValueError("readiness promotion changed unexpected provider fields")
    if before_target.get("live_auth_verified") is not False:
        raise ValueError("provider already live-auth promoted")
    if after_target.get("live_auth_verified") is not True:
        raise ValueError("provider live-auth promotion missing")

    body={
        "apply_status":"VALID_LIVE_AUTH_PROMOTION_APPLY",
        "provider":provider,
        "claim":"live_auth_verified",
        "source_probe_run_id":verified_package["source_probe_run_id"],
        "review_run_id":verified_package["review_run_id"],
        "promotion_preview_run_id":verified_package[
            "promotion_preview_run_id"
        ],
        "promotion_preview_commit":verified_package[
            "promotion_preview_commit"
        ],
        "promotion_preview_sha256":fresh["preview_sha256"],
        "global_provider_gate":gate,
        "forecast_enabled":False,
        "network_autorun_enabled":False,
        "forecast_activation_permitted":False,
        "provider_network_request_permitted":False,
        "updated_readiness":updated_readiness,
        "updated_ledger":updated_ledger,
    }
    result=dict(body)
    result["apply_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return result
