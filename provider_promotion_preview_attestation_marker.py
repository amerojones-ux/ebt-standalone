"""Validate promotion-preview attestation verification markers."""
import hashlib
import hmac
import json
import re

SOURCE_REPOSITORY="amerojones-ux/ebt-standalone"
PROMOTION_WORKFLOW=".github/workflows/provider-live-auth-promotion-preview.yml"
SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
ATTESTATION_ID=re.compile(r"^[A-Za-z0-9._:-]+$")

BODY_FIELDS={
    "schema_version","verification_status","repository",
    "promotion_workflow_run_id","promotion_workflow_run_attempt",
    "review_workflow_run_id","source_probe_run_id",
    "source_commit","source_ref","signer_workflow",
    "preview_file","preview_sha256","preview_file_sha256",
    "global_provider_gate","attestation_id","attestation_url",
    "verification_tool",
}
ALL_FIELDS=BODY_FIELDS|{"marker_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_promotion_preview_attestation_marker(
    marker,
    *,
    expected_run_id,
    expected_commit,
    expected_review_run_id=None,
    expected_source_probe_run_id=None,
):
    if not isinstance(marker,dict) or set(marker)!=ALL_FIELDS:
        return False
    if marker.get("schema_version")!=2:
        return False
    if marker.get("verification_status")!="VERIFIED":
        return False
    if marker.get("repository")!=SOURCE_REPOSITORY:
        return False

    run_id=marker.get("promotion_workflow_run_id")
    if run_id!=expected_run_id or not isinstance(run_id,str) or not RUN_ID.fullmatch(run_id):
        return False
    if (
        type(marker.get("promotion_workflow_run_attempt")) is not int
        or marker["promotion_workflow_run_attempt"]!=1
    ):
        return False

    review_run_id=marker.get("review_workflow_run_id")
    source_probe_run_id=marker.get("source_probe_run_id")
    if not isinstance(review_run_id,str) or not RUN_ID.fullmatch(review_run_id):
        return False
    if not isinstance(source_probe_run_id,str) or not RUN_ID.fullmatch(source_probe_run_id):
        return False
    if expected_review_run_id is not None and review_run_id!=expected_review_run_id:
        return False
    if (
        expected_source_probe_run_id is not None
        and source_probe_run_id!=expected_source_probe_run_id
    ):
        return False

    commit=marker.get("source_commit")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        return False
    if commit.lower()!=expected_commit.lower():
        return False
    if marker.get("source_ref")!="refs/heads/main":
        return False
    if marker.get("signer_workflow")!=PROMOTION_WORKFLOW:
        return False
    if marker.get("preview_file")!="provider_live_auth_promotion_preview.json":
        return False
    for field in ("preview_sha256","preview_file_sha256"):
        value=marker.get(field)
        if not isinstance(value,str) or not SHA64.fullmatch(value):
            return False
    if marker.get("global_provider_gate")!="SAFE_HOLD":
        return False

    attestation_id=marker.get("attestation_id")
    if not isinstance(attestation_id,str) or not ATTESTATION_ID.fullmatch(attestation_id):
        return False
    url=marker.get("attestation_url")
    if not isinstance(url,str) or not url.startswith(
        "https://github.com/"+SOURCE_REPOSITORY+"/attestations/"
    ):
        return False
    if marker.get("verification_tool")!="gh attestation verify":
        return False

    expected=marker.get("marker_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:marker[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
