"""Validate execution-intent attestation verification markers."""
import hashlib
import hmac
import json
import re

from provider_execution_intent import CONTRACTS, REPOSITORY
from provider_live_request_plan import request_plan_sha256

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
ACTOR=re.compile(r"^[A-Za-z0-9-]+$")
ACTOR_ID=re.compile(r"^[0-9]+$")
ATTESTATION_ID=re.compile(r"^[A-Za-z0-9._:-]+$")
PYTHON_VERSION=re.compile(r"^3\.13\.\d+$")
GH_VERSION=re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?$")

RUNNER_LABEL="ubuntu-24.04"
SETUP_PYTHON_SHA="6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"
VERIFICATION_MODES=["local_bundle","github_api"]

BODY_FIELDS={
    "schema_version","provider","verification_status","repository",
    "workflow_run_id","workflow_run_attempt","source_commit","source_ref","signer_workflow",
    "actor","actor_id","intent_sha256","intent_file_sha256",
    "request_plan_sha256","max_requests",
    "attestation_id","attestation_url","attestation_bundle_sha256",
    "verification_tool","verification_modes","runner_label",
    "python_version","gh_version","setup_python_sha",
}
ALL_FIELDS=BODY_FIELDS|{"marker_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_execution_intent_marker(
    marker,
    *,
    provider,
    expected_run_id,
    expected_commit,
):
    contract=CONTRACTS.get(provider)
    if contract is None:
        return False
    if not isinstance(marker,dict) or set(marker)!=ALL_FIELDS:
        return False
    if marker.get("schema_version")!=2:
        return False
    if marker.get("provider")!=provider:
        return False
    if marker.get("verification_status")!="VERIFIED":
        return False
    if marker.get("repository")!=REPOSITORY:
        return False
    if marker.get("workflow_run_id")!=expected_run_id:
        return False
    if not RUN_ID.fullmatch(marker.get("workflow_run_id","")):
        return False
    if type(marker.get("workflow_run_attempt")) is not int or marker["workflow_run_attempt"]!=1:
        return False
    commit=marker.get("source_commit")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        return False
    if commit.lower()!=expected_commit.lower():
        return False
    if marker.get("source_ref")!="refs/heads/main":
        return False
    if marker.get("signer_workflow")!=contract["workflow"]:
        return False
    if not ACTOR.fullmatch(marker.get("actor","")):
        return False
    if not ACTOR_ID.fullmatch(marker.get("actor_id","")):
        return False
    for field in (
        "intent_sha256","intent_file_sha256",
        "request_plan_sha256","attestation_bundle_sha256",
    ):
        value=marker.get(field)
        if not isinstance(value,str) or not SHA64.fullmatch(value):
            return False
    if marker.get("request_plan_sha256")!=request_plan_sha256(provider):
        return False
    if type(marker.get("max_requests")) is not int or marker["max_requests"]!=1:
        return False
    attestation_id=marker.get("attestation_id")
    if not isinstance(attestation_id,str) or not ATTESTATION_ID.fullmatch(attestation_id):
        return False
    url=marker.get("attestation_url")
    if not isinstance(url,str) or not url.startswith(
        "https://github.com/"+REPOSITORY+"/attestations/"
    ):
        return False
    if marker.get("verification_tool")!="gh attestation verify":
        return False
    if marker.get("verification_modes")!=VERIFICATION_MODES:
        return False
    if marker.get("runner_label")!=RUNNER_LABEL:
        return False
    python_version=marker.get("python_version")
    if not isinstance(python_version,str) or not PYTHON_VERSION.fullmatch(python_version):
        return False
    gh_version=marker.get("gh_version")
    if not isinstance(gh_version,str) or not GH_VERSION.fullmatch(gh_version):
        return False
    if marker.get("setup_python_sha")!=SETUP_PYTHON_SHA:
        return False

    expected=marker.get("marker_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:marker[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
