"""Non-mutating live-auth promotion preview.

Consumes an approved attested review decision, previews the evidence-ledger insert,
then previews setting only provider.live_auth_verified=true. It refuses any result
that is not still SAFE_HOLD.
"""
import copy
import hashlib
import json

from provider_activation_gate import status, validate_config
from provider_evidence_ledger_preview import build_ledger_preview
from provider_readiness_evidence_gate import evidence_supports_readiness

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def build_live_auth_promotion_preview(
    readiness,
    ledger,
    attested_review_decision,
    *,
    trusted_now,
):
    config_errors=validate_config(readiness)
    if config_errors:
        raise ValueError("current readiness config invalid")

    ledger_preview=build_ledger_preview(
        ledger,attested_review_decision,trusted_now=trusted_now
    )
    if ledger_preview.get("claim")!="live_auth_verified":
        raise ValueError("review decision is not live-auth evidence")

    provider=ledger_preview["subject"]
    updated=copy.deepcopy(readiness)

    target=None
    for entry in updated["providers"]:
        if entry.get("name")==provider:
            target=entry
            break
    if target is None:
        raise ValueError("provider missing from readiness config")
    if target.get("live_auth_verified") is not False:
        raise ValueError("refusing to overwrite live_auth_verified")

    before=copy.deepcopy(target)
    target["live_auth_verified"]=True

    allowed_change={"live_auth_verified"}
    changed={
        key for key in set(before)|set(target)
        if before.get(key)!=target.get(key)
    }
    if changed!=allowed_change:
        raise ValueError("promotion changed fields beyond live_auth_verified")

    post_config_errors=validate_config(updated)
    if post_config_errors:
        raise ValueError("proposed readiness config invalid")

    evidence_errors=evidence_supports_readiness(
        updated,
        ledger_preview["preview_ledger"],
        trusted_now=trusted_now,
    )
    if evidence_errors:
        raise ValueError("proposed readiness lacks valid evidence")

    gate=status(updated,evidence_ok=True)
    if gate!="SAFE_HOLD":
        raise ValueError("live-auth promotion must not cross activation boundary")

    body={
        "preview_status":"VALID_LIVE_AUTH_PROMOTION_PREVIEW",
        "provider":provider,
        "claim":"live_auth_verified",
        "decision_sha256":ledger_preview["decision_sha256"],
        "global_provider_gate":gate,
        "ledger_write_permitted":False,
        "readiness_write_permitted":False,
        "forecast_activation_permitted":False,
        "preview_ledger":ledger_preview["preview_ledger"],
        "preview_readiness":updated,
    }
    result=dict(body)
    result["preview_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return result
