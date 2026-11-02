"""Validate sanitized attestation-verification markers emitted by probe workflows."""
import hashlib
import hmac
import json
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
ATTESTATION_ID=re.compile(r"^[A-Za-z0-9._:-]+$")

EXPECTED={
    "WeatherAPI":{
        "receipt_file":"weatherapi_probe_receipt.json",
        "signer_workflow":".github/workflows/weatherapi-live-probe.yml",
    },
    "The Odds API":{
        "receipt_file":"theoddsapi_probe_receipt.json",
        "signer_workflow":".github/workflows/theoddsapi-live-probe.yml",
    },
    "API-Sports":{
        "receipt_file":"apisports_status_receipt.json",
        "signer_workflow":".github/workflows/apisports-status-probe.yml",
    },
}

BODY_FIELDS={
    "schema_version","provider","verification_status","repository",
    "workflow_run_id","source_commit","source_ref","signer_workflow",
    "attestation_id","attestation_url","receipt_file","verification_tool",
}
ALL_FIELDS=BODY_FIELDS|{"marker_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_marker(marker, *, provider, repository, expected_run_id, expected_commit):
    if provider not in EXPECTED:
        return False
    if not isinstance(marker,dict) or set(marker)!=ALL_FIELDS:
        return False
    if marker.get("schema_version")!=1:
        return False
    if marker.get("provider")!=provider:
        return False
    if marker.get("verification_status")!="VERIFIED":
        return False
    if marker.get("repository")!=repository:
        return False
    if marker.get("workflow_run_id")!=expected_run_id:
        return False
    if not RUN_ID.fullmatch(marker.get("workflow_run_id","")):
        return False
    commit=marker.get("source_commit")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        return False
    if commit.lower()!=expected_commit.lower():
        return False
    if marker.get("source_ref")!="refs/heads/main":
        return False

    spec=EXPECTED[provider]
    if marker.get("signer_workflow")!=spec["signer_workflow"]:
        return False
    if marker.get("receipt_file")!=spec["receipt_file"]:
        return False
    if marker.get("verification_tool")!="gh attestation verify":
        return False

    attestation_id=marker.get("attestation_id")
    if not isinstance(attestation_id,str) or not attestation_id:
        return False
    if not ATTESTATION_ID.fullmatch(attestation_id):
        return False

    url=marker.get("attestation_url")
    if not isinstance(url,str) or not url.startswith(
        "https://github.com/"+repository+"/attestations/"
    ):
        return False

    expected=marker.get("marker_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={k:marker[k] for k in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
