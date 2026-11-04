"""Drift-checked non-mutating provider account-metadata promotion preview."""
import hashlib
import hmac
import json

from provider_account_metadata_claim import verify_account_metadata_claim
from provider_account_metadata_source_review import verify_source_review_decision
from provider_account_metadata_transition import build_transition, load_configs
from provider_account_evidence import load_registry

BODY_FIELDS={
    "schema_version","preview_type","preview_status","provider",
    "source_claim_run_id","source_claim_sha256","source_review_decision_sha256",
    "source_reference","source_type","current_state_sha256",
    "rebuilt_transition_sha256","candidate_registry","candidate_configs",
    "metadata_write_permitted","network_request_permitted",
    "forecast_activation_permitted","model_evidence_allowed",
}
ALL_FIELDS=BODY_FIELDS|{"preview_sha256"}

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()

def _state_payload(registry,configs):
    return {"registry":registry,"configs":configs}

def build_metadata_promotion_preview(claim,decision,*,registry=None,configs=None):
    if not verify_account_metadata_claim(claim):
        raise ValueError("account metadata claim invalid")
    if not verify_source_review_decision(decision):
        raise ValueError("source review decision invalid")
    if decision.get("decision")!="APPROVE":
        raise ValueError("source review decision must be APPROVE")
    if decision.get("provider")!=claim.get("provider"):
        raise ValueError("provider binding mismatch")
    if decision.get("source_claim_run_id")!=str(claim.get("workflow_run_id")):
        raise ValueError("claim run binding mismatch")
    if decision.get("source_claim_sha256")!=claim.get("claim_sha256"):
        raise ValueError("claim checksum binding mismatch")
    if decision.get("source_claim_commit")!=claim.get("source_commit"):
        raise ValueError("claim commit binding mismatch")
    if decision.get("source_type")!=claim.get("source_type"):
        raise ValueError("source type binding mismatch")
    if decision.get("source_reference")!=claim.get("source_reference"):
        raise ValueError("source reference binding mismatch")
    if decision.get("claim_verified_against_provider_source") is not True:
        raise ValueError("claim not source verified")
    if decision.get("approved_transition")!=claim.get("transition"):
        raise ValueError("approved transition differs from signed claim")

    if registry is None:
        registry=load_registry()
    if configs is None:
        configs=load_configs()

    rebuilt=build_transition(
        claim["provider"],
        claim["submitted_facts"],
        registry=registry,
        configs=configs,
    )
    if rebuilt.get("status")!="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW":
        raise ValueError("current-state transition rebuild HOLD")
    if rebuilt!=claim.get("transition"):
        raise ValueError("current committed state drifted from signed claim transition")
    if rebuilt!=decision.get("approved_transition"):
        raise ValueError("current rebuilt transition differs from approved transition")

    body={
        "schema_version":1,
        "preview_type":"ACCOUNT_METADATA_PROMOTION_PREVIEW",
        "preview_status":"VALID_ACCOUNT_METADATA_PROMOTION_PREVIEW",
        "provider":claim["provider"],
        "source_claim_run_id":str(claim["workflow_run_id"]),
        "source_claim_sha256":claim["claim_sha256"],
        "source_review_decision_sha256":decision["decision_sha256"],
        "source_reference":claim["source_reference"],
        "source_type":claim["source_type"],
        "current_state_sha256":_sha(_state_payload(registry,configs)),
        "rebuilt_transition_sha256":_sha(rebuilt),
        "candidate_registry":rebuilt["candidate_registry"],
        "candidate_configs":rebuilt["candidate_configs"],
        "metadata_write_permitted":False,
        "network_request_permitted":False,
        "forecast_activation_permitted":False,
        "model_evidence_allowed":False,
    }
    out=dict(body)
    out["preview_sha256"]=_sha(body)
    return out

def verify_metadata_promotion_preview(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    if value.get("schema_version")!=1:
        return False
    if value.get("preview_type")!="ACCOUNT_METADATA_PROMOTION_PREVIEW":
        return False
    if value.get("preview_status")!="VALID_ACCOUNT_METADATA_PROMOTION_PREVIEW":
        return False
    if value.get("provider") not in {"SportsDataIO","Sportradar","RapidAPI"}:
        return False
    for key in (
        "source_claim_sha256","source_review_decision_sha256",
        "current_state_sha256","rebuilt_transition_sha256","preview_sha256",
    ):
        val=value.get(key)
        if not isinstance(val,str) or len(val)!=64:
            return False
    if not isinstance(value.get("source_claim_run_id"),str) or not value["source_claim_run_id"].isdigit():
        return False
    if not isinstance(value.get("source_reference"),str) or not value["source_reference"]:
        return False
    if value.get("source_type") not in {"ACCOUNT_PORTAL","PROVIDER_SUPPORT"}:
        return False
    if not isinstance(value.get("candidate_registry"),dict):
        return False
    if not isinstance(value.get("candidate_configs"),dict):
        return False
    if set(value["candidate_configs"])!={"SportsDataIO","Sportradar","RapidAPI"}:
        return False
    for key in (
        "metadata_write_permitted","network_request_permitted",
        "forecast_activation_permitted","model_evidence_allowed",
    ):
        if value.get(key) is not False:
            return False
    body={k:value[k] for k in BODY_FIELDS}
    expected=_sha(body)
    return hmac.compare_digest(expected,value["preview_sha256"])
