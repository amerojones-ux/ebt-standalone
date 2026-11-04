"""Verifier for signed nonsecret provider account-metadata claims.

This verifier proves claim structure/checksum and safety semantics. It does not
prove the underlying provider portal/support fact is true.
"""
import hashlib
import json
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
SUBMITTER=re.compile(r"^github:[A-Za-z0-9-]+#[0-9]+$")
PROVIDERS={"SportsDataIO","Sportradar","RapidAPI"}
SOURCE_TYPES={"ACCOUNT_PORTAL","PROVIDER_SUPPORT"}

BODY_FIELDS={
    "schema_version","claim_type","provider","source_type","source_reference",
    "submitter","repository","workflow_run_id","workflow_run_attempt",
    "source_commit","transition","claim_verified_against_provider_source",
    "write_permitted","network_request_permitted",
    "forecast_activation_permitted",
}
ALL_FIELDS=BODY_FIELDS|{"claim_sha256"}

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_account_metadata_claim(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    if value.get("schema_version")!=1:
        return False
    if value.get("claim_type")!="ACCOUNT_METADATA_CLAIM":
        return False
    if value.get("provider") not in PROVIDERS:
        return False
    if value.get("source_type") not in SOURCE_TYPES:
        return False
    ref=value.get("source_reference")
    if not isinstance(ref,str) or not re.fullmatch(r"[A-Za-z0-9 ._/#()-]{1,160}",ref):
        return False
    if not SUBMITTER.fullmatch(value.get("submitter","")):
        return False
    if value.get("repository")!="amerojones-ux/ebt-standalone":
        return False
    if not RUN_ID.fullmatch(str(value.get("workflow_run_id",""))):
        return False
    if value.get("workflow_run_attempt")!=1:
        return False
    if not SHA40.fullmatch(value.get("source_commit","")):
        return False
    transition=value.get("transition")
    if not isinstance(transition,dict):
        return False
    if transition.get("provider")!=value.get("provider"):
        return False
    if transition.get("status")!="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW":
        return False
    for key in (
        "write_permitted","network_request_permitted",
        "forecast_activation_permitted","model_evidence_allowed",
    ):
        if transition.get(key) is not False:
            return False
    if value.get("claim_verified_against_provider_source") is not False:
        return False
    for key in (
        "write_permitted","network_request_permitted",
        "forecast_activation_permitted",
    ):
        if value.get(key) is not False:
            return False
    checksum=value.get("claim_sha256")
    if not SHA64.fullmatch(checksum or ""):
        return False
    body={k:value[k] for k in BODY_FIELDS}
    expected=hashlib.sha256(_canonical(body)).hexdigest()
    return expected==checksum
