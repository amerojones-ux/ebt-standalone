"""Validate signed review-decision attestation verification markers."""
import hashlib
import hmac
import json
import re

SOURCE_REPOSITORY="amerojones-ux/ebt-standalone"
REVIEW_WORKFLOW=".github/workflows/provider-live-auth-evidence-review.yml"
SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
REVIEWER=re.compile(r"^github:[A-Za-z0-9-]+#[0-9]+$")
ATTESTATION_ID=re.compile(r"^[A-Za-z0-9._:-]+$")

BODY_FIELDS={
    "schema_version","verification_status","repository",
    "review_workflow_run_id","review_workflow_run_attempt","source_commit","source_ref",
    "signer_workflow","reviewer","attestation_id","attestation_url",
    "decision_file","verification_tool",
}
ALL_FIELDS=BODY_FIELDS|{"marker_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_review_attestation_marker(
    marker,
    *,
    expected_run_id,
    expected_commit,
):
    if not isinstance(marker,dict) or set(marker)!=ALL_FIELDS:
        return False
    if marker.get("schema_version")!=2:
        return False
    if marker.get("verification_status")!="VERIFIED":
        return False
    if marker.get("repository")!=SOURCE_REPOSITORY:
        return False
    if marker.get("review_workflow_run_id")!=expected_run_id:
        return False
    if not RUN_ID.fullmatch(marker.get("review_workflow_run_id","")):
        return False
    if type(marker.get("review_workflow_run_attempt")) is not int or marker["review_workflow_run_attempt"]!=1:
        return False
    commit=marker.get("source_commit")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        return False
    if commit.lower()!=expected_commit.lower():
        return False
    if marker.get("source_ref")!="refs/heads/main":
        return False
    if marker.get("signer_workflow")!=REVIEW_WORKFLOW:
        return False
    if not REVIEWER.fullmatch(marker.get("reviewer","")):
        return False
    attestation_id=marker.get("attestation_id")
    if not isinstance(attestation_id,str) or not ATTESTATION_ID.fullmatch(attestation_id):
        return False
    url=marker.get("attestation_url")
    if not isinstance(url,str) or not url.startswith(
        "https://github.com/"+SOURCE_REPOSITORY+"/attestations/"
    ):
        return False
    if marker.get("decision_file")!="provider_review_decision.json":
        return False
    if marker.get("verification_tool")!="gh attestation verify":
        return False
    expected=marker.get("marker_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:marker[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
