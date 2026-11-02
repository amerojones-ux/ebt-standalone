"""Convert supported sanitized provider PASS receipts into review-only evidence candidates.

This module never edits provider readiness or the evidence ledger. It produces a
candidate that still requires an authorized reviewer to create a VERIFIED ledger record.
"""
import hashlib
import json
import re

from apisports_status_receipt import verify_receipt as verify_apisports
from theoddsapi_probe_receipt import verify_receipt as verify_theodds
from weatherapi_probe_receipt import verify_receipt as verify_weather

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")

SUPPORTED={
    "WeatherAPI":{
        "verify":verify_weather,
        "pass_category":"authenticated_schema_fresh",
    },
    "The Odds API":{
        "verify":verify_theodds,
        "pass_category":"authenticated_zero_credit_sports_schema",
    },
    "API-Sports":{
        "verify":verify_apisports,
        "pass_category":"authenticated_status_schema",
    },
}

def build_review_candidate(receipt, *, artifact_sha256, expected_run_id, expected_commit):
    if not isinstance(receipt,dict):
        raise ValueError("receipt must be object")
    provider=receipt.get("provider")
    spec=SUPPORTED.get(provider)
    if spec is None:
        raise ValueError("unsupported receipt provider")
    if not spec["verify"](receipt):
        raise ValueError("receipt verification failed")
    if receipt.get("status")!="PASS":
        raise ValueError("only PASS receipts are promotable to review")
    if receipt.get("category")!=spec["pass_category"]:
        raise ValueError("unexpected PASS category")

    commit=receipt.get("git_commit")
    run_id=receipt.get("github_run_id")
    receipt_digest=receipt.get("receipt_sha256")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        raise ValueError("GitHub source commit required")
    if not isinstance(run_id,str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("GitHub run id required")
    if not isinstance(receipt_digest,str) or not SHA64.fullmatch(receipt_digest):
        raise ValueError("receipt checksum required")
    if not isinstance(artifact_sha256,str) or not SHA64.fullmatch(artifact_sha256):
        raise ValueError("artifact file checksum required")
    if not isinstance(expected_run_id,str) or not RUN_ID.fullmatch(expected_run_id):
        raise ValueError("trusted GitHub run id required")
    if not isinstance(expected_commit,str) or not SHA40.fullmatch(expected_commit):
        raise ValueError("trusted GitHub head commit required")
    if run_id != expected_run_id:
        raise ValueError("receipt run id does not match trusted GitHub run")
    if commit.lower() != expected_commit.lower():
        raise ValueError("receipt commit does not match trusted GitHub head commit")

    body={
        "provider":provider,
        "subject":provider,
        "claim":"live_auth_verified",
        "candidate_status":"REVIEW_ONLY",
        "source_type":"github_actions_receipt",
        "reference":"github-actions-run:"+run_id,
        "source_commit":commit.lower(),
        "github_binding_verified":True,
        "receipt_sha256":receipt_digest,
        "artifact_sha256":artifact_sha256.lower(),
        "reviewer_required":True,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
    canonical=json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")
    candidate=dict(body)
    candidate["candidate_sha256"]=hashlib.sha256(canonical).hexdigest()
    return candidate
