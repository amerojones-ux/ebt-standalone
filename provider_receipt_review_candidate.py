"""Build receipt-derived candidates, then bind verified attestation evidence.

A receipt alone can create only REVIEW_ONLY_PENDING_ATTESTATION. Reviewer-eligible
REVIEW_ONLY status requires a separate verified attestation marker binding.
"""
import hashlib
import hmac
import json
import re

from therundown_probe_receipt import verify_receipt as verify_therundown
from apisports_status_receipt import verify_receipt as verify_apisports
from theoddsapi_probe_receipt import verify_receipt as verify_theodds
from weatherapi_probe_receipt import verify_receipt as verify_weather
from provider_live_request_plan import request_plan_sha256 as canonical_request_plan_sha256

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
ACTOR=re.compile(r"^[A-Za-z0-9-]+$")
ACTOR_ID=re.compile(r"^[0-9]+$")
SOURCE_REPOSITORY="amerojones-ux/ebt-standalone"
SIGNER_WORKFLOWS={
    "WeatherAPI":".github/workflows/weatherapi-live-probe.yml",
    "The Odds API":".github/workflows/theoddsapi-live-probe.yml",
    "TheRundown":".github/workflows/therundown-live-probe.yml",
    "API-Sports":".github/workflows/apisports-status-probe.yml",
}

SUPPORTED={
    "WeatherAPI":{
        "verify":verify_weather,
        "pass_category":"authenticated_schema_fresh",
    },
    "The Odds API":{
        "verify":verify_theodds,
        "pass_category":"authenticated_zero_credit_sports_schema",
    },
    "TheRundown":{
        "verify":verify_therundown,
        "pass_category":"authenticated_zero_datapoint_sample_json",
    },
    "API-Sports":{
        "verify":verify_apisports,
        "pass_category":"authenticated_status_schema",
    },
}

BODY_FIELDS={
    "provider","subject","claim","candidate_status","source_type","reference",
    "source_repository","source_commit","github_metadata_match",
    "receipt_sha256","artifact_sha256","attestation_verified",
    "attestation_marker_sha256","request_plan_sha256","attestation_id","attestation_url",
    "signer_workflow","execution_intent_verified","execution_intent_sha256",
    "execution_intent_file_sha256","execution_intent_marker_sha256",
    "execution_intent_bundle_sha256","execution_intent_attestation_id",
    "execution_intent_attestation_url","execution_actor","execution_actor_id",
    "execution_max_requests","reviewer_required",
    "readiness_mutation_permitted","forecast_activation_permitted",
}
ALL_FIELDS=BODY_FIELDS|{"candidate_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def _sign(body):
    candidate=dict(body)
    candidate["candidate_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return candidate

def verify_candidate_checksum(candidate):
    if not isinstance(candidate,dict) or set(candidate)!=ALL_FIELDS:
        return False
    expected=candidate.get("candidate_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={k:candidate[k] for k in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)

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

    return _sign({
        "provider":provider,
        "subject":provider,
        "claim":"live_auth_verified",
        "candidate_status":"REVIEW_ONLY_PENDING_ATTESTATION",
        "source_type":"github_actions_receipt",
        "reference":"github-actions-run:"+run_id,
        "source_repository":None,
        "source_commit":commit.lower(),
        "github_metadata_match":True,
        "receipt_sha256":receipt_digest,
        "artifact_sha256":artifact_sha256.lower(),
        "attestation_verified":False,
        "attestation_marker_sha256":None,
        "request_plan_sha256":None,
        "attestation_id":None,
        "attestation_url":None,
        "signer_workflow":None,
        "execution_intent_verified":False,
        "execution_intent_sha256":receipt["execution_intent_sha256"],
        "execution_intent_file_sha256":None,
        "execution_intent_marker_sha256":None,
        "execution_intent_bundle_sha256":None,
        "execution_intent_attestation_id":None,
        "execution_intent_attestation_url":None,
        "execution_actor":None,
        "execution_actor_id":None,
        "execution_max_requests":None,
        "reviewer_required":True,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    })

def bind_attestation_verification(
    candidate,
    *,
    marker_sha256,
    request_plan_sha256,
    source_repository,
    attestation_id,
    attestation_url,
    signer_workflow,
    execution_intent_sha256,
    execution_intent_file_sha256,
    execution_intent_marker_sha256,
    execution_intent_bundle_sha256,
    execution_intent_attestation_id,
    execution_intent_attestation_url,
    execution_actor,
    execution_actor_id,
    execution_max_requests,
):
    if not verify_candidate_checksum(candidate):
        raise ValueError("candidate checksum invalid")
    if candidate.get("candidate_status")!="REVIEW_ONLY_PENDING_ATTESTATION":
        raise ValueError("candidate is not pending attestation")
    if candidate.get("attestation_verified") is not False:
        raise ValueError("candidate attestation state invalid")
    if candidate.get("attestation_marker_sha256") is not None:
        raise ValueError("candidate already has attestation marker")
    if not isinstance(marker_sha256,str) or not SHA64.fullmatch(marker_sha256):
        raise ValueError("valid attestation marker checksum required")
    if not isinstance(request_plan_sha256,str) or not SHA64.fullmatch(request_plan_sha256):
        raise ValueError("valid request plan checksum required")
    if request_plan_sha256.lower()!=canonical_request_plan_sha256(
        candidate.get("provider")
    ):
        raise ValueError("request plan checksum mismatch")
    if source_repository != SOURCE_REPOSITORY:
        raise ValueError("source repository mismatch")
    if not isinstance(attestation_id,str) or not attestation_id:
        raise ValueError("attestation id required")
    if not isinstance(attestation_url,str) or not attestation_url.startswith(
        "https://github.com/"+source_repository+"/attestations/"
    ):
        raise ValueError("attestation url/repository mismatch")
    expected_signer=SIGNER_WORKFLOWS.get(candidate.get("provider"))
    if signer_workflow != expected_signer:
        raise ValueError("signer workflow mismatch")

    if candidate.get("execution_intent_sha256")!=str(
        execution_intent_sha256
    ).lower():
        raise ValueError("receipt/execution-intent checksum binding mismatch")
    for label,value in (
        ("execution_intent_sha256",execution_intent_sha256),
        ("execution_intent_file_sha256",execution_intent_file_sha256),
        ("execution_intent_marker_sha256",execution_intent_marker_sha256),
        ("execution_intent_bundle_sha256",execution_intent_bundle_sha256),
    ):
        if not isinstance(value,str) or not SHA64.fullmatch(value):
            raise ValueError("valid "+label+" required")
    if not isinstance(execution_intent_attestation_id,str) or not execution_intent_attestation_id:
        raise ValueError("execution intent attestation id required")
    if (
        not isinstance(execution_intent_attestation_url,str)
        or not execution_intent_attestation_url.startswith(
            "https://github.com/"+source_repository+"/attestations/"
        )
    ):
        raise ValueError("execution intent attestation url/repository mismatch")
    if not isinstance(execution_actor,str) or not ACTOR.fullmatch(execution_actor):
        raise ValueError("execution actor invalid")
    if not isinstance(execution_actor_id,str) or not ACTOR_ID.fullmatch(execution_actor_id):
        raise ValueError("execution actor id invalid")
    if type(execution_max_requests) is not int or execution_max_requests!=1:
        raise ValueError("execution intent must authorize exactly one request")

    body={k:candidate[k] for k in BODY_FIELDS}
    body["candidate_status"]="REVIEW_ONLY"
    body["source_repository"]=source_repository
    body["attestation_verified"]=True
    body["attestation_marker_sha256"]=marker_sha256.lower()
    body["request_plan_sha256"]=request_plan_sha256.lower()
    body["attestation_id"]=attestation_id
    body["attestation_url"]=attestation_url
    body["signer_workflow"]=signer_workflow
    body["execution_intent_verified"]=True
    body["execution_intent_sha256"]=execution_intent_sha256.lower()
    body["execution_intent_file_sha256"]=execution_intent_file_sha256.lower()
    body["execution_intent_marker_sha256"]=execution_intent_marker_sha256.lower()
    body["execution_intent_bundle_sha256"]=execution_intent_bundle_sha256.lower()
    body["execution_intent_attestation_id"]=execution_intent_attestation_id
    body["execution_intent_attestation_url"]=execution_intent_attestation_url
    body["execution_actor"]=execution_actor
    body["execution_actor_id"]=execution_actor_id
    body["execution_max_requests"]=execution_max_requests
    return _sign(body)
