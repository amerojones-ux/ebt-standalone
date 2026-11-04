"""Source-review decision for an attested provider account-metadata claim.

Approval means a GitHub reviewer asserts the claim was checked against the
underlying provider portal/support source and matched it. Approval is still
non-mutating and does not authorize provider network access or forecasting.
"""
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone

from provider_account_metadata_claim import verify_account_metadata_claim

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
REVIEWER=re.compile(r"^github:[A-Za-z0-9-]+#[0-9]+$")
SAFE_REF=re.compile(r"^[A-Za-z0-9 ._/#()-]{1,160}$")
PROVIDERS={"SportsDataIO","Sportradar","RapidAPI"}

BODY_FIELDS={
    "schema_version","decision_type","provider","decision",
    "source_claim_run_id","source_claim_sha256","source_claim_commit",
    "source_type","source_reference","reviewer","reviewed_at",
    "provider_source_reviewed","provider_source_match",
    "claim_verified_against_provider_source","approved_transition",
    "metadata_promotion_permitted","network_request_permitted",
    "forecast_activation_permitted","model_evidence_allowed",
}
ALL_FIELDS=BODY_FIELDS|{"decision_sha256"}

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def _parse_time(value):
    if not isinstance(value,str) or not value:
        return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed

def build_source_review_decision(claim,*,decision,reviewer,source_reference,reviewed_at=None):
    if not verify_account_metadata_claim(claim):
        raise ValueError("account metadata claim invalid")
    if decision not in {"APPROVE","REJECT"}:
        raise ValueError("decision must be APPROVE or REJECT")
    if not REVIEWER.fullmatch(reviewer or ""):
        raise ValueError("reviewer invalid")
    if not isinstance(source_reference,str) or not SAFE_REF.fullmatch(source_reference):
        raise ValueError("source reference invalid")
    if source_reference!=claim.get("source_reference"):
        raise ValueError("source reference does not match signed claim")
    if reviewed_at is None:
        reviewed_at=datetime.now(timezone.utc).isoformat()
    if _parse_time(reviewed_at) is None:
        raise ValueError("reviewed_at invalid")

    approved=decision=="APPROVE"
    body={
        "schema_version":1,
        "decision_type":"ACCOUNT_METADATA_SOURCE_REVIEW",
        "provider":claim["provider"],
        "decision":decision,
        "source_claim_run_id":str(claim["workflow_run_id"]),
        "source_claim_sha256":claim["claim_sha256"],
        "source_claim_commit":claim["source_commit"],
        "source_type":claim["source_type"],
        "source_reference":source_reference,
        "reviewer":reviewer,
        "reviewed_at":reviewed_at,
        "provider_source_reviewed":True,
        "provider_source_match":approved,
        "claim_verified_against_provider_source":approved,
        "approved_transition":claim["transition"] if approved else None,
        "metadata_promotion_permitted":False,
        "network_request_permitted":False,
        "forecast_activation_permitted":False,
        "model_evidence_allowed":False,
    }
    result=dict(body)
    result["decision_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return result

def verify_source_review_decision(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    if value.get("schema_version")!=1:
        return False
    if value.get("decision_type")!="ACCOUNT_METADATA_SOURCE_REVIEW":
        return False
    if value.get("provider") not in PROVIDERS:
        return False
    if value.get("decision") not in {"APPROVE","REJECT"}:
        return False
    if not RUN_ID.fullmatch(value.get("source_claim_run_id","")):
        return False
    if not SHA64.fullmatch(value.get("source_claim_sha256","")):
        return False
    if not SHA40.fullmatch(value.get("source_claim_commit","")):
        return False
    if value.get("source_type") not in {"ACCOUNT_PORTAL","PROVIDER_SUPPORT"}:
        return False
    if not isinstance(value.get("source_reference"),str) or not SAFE_REF.fullmatch(value["source_reference"]):
        return False
    if not REVIEWER.fullmatch(value.get("reviewer","")):
        return False
    if _parse_time(value.get("reviewed_at")) is None:
        return False
    if value.get("provider_source_reviewed") is not True:
        return False

    approved=value["decision"]=="APPROVE"
    if value.get("provider_source_match") is not approved:
        return False
    if value.get("claim_verified_against_provider_source") is not approved:
        return False
    transition=value.get("approved_transition")
    if approved:
        if not isinstance(transition,dict):
            return False
        if transition.get("provider")!=value["provider"]:
            return False
        if transition.get("status")!="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW":
            return False
        for key in (
            "write_permitted","network_request_permitted",
            "forecast_activation_permitted","model_evidence_allowed",
        ):
            if transition.get(key) is not False:
                return False
    elif transition is not None:
        return False

    for key in (
        "metadata_promotion_permitted","network_request_permitted",
        "forecast_activation_permitted","model_evidence_allowed",
    ):
        if value.get(key) is not False:
            return False

    expected=value.get("decision_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={k:value[k] for k in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
