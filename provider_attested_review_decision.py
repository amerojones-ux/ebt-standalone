"""Checksum-bound review decision after GitHub review-attestation verification."""
import hashlib
import hmac
import json
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_ID=re.compile(r"^[0-9]+$")
REVIEWER=re.compile(r"^github:[A-Za-z0-9-]+#[0-9]+$")
SOURCE_REPOSITORY="amerojones-ux/ebt-standalone"
REVIEW_WORKFLOW=".github/workflows/provider-live-auth-evidence-review.yml"

BODY_FIELDS={
    "subject","claim","decision","reviewer","reviewed_at",
    "candidate_sha256","decision_sha256","attested_status",
    "review_repository","review_workflow_run_id","review_source_commit",
    "review_github_metadata_match","review_decision_file_sha256",
    "review_attestation_marker_sha256","review_attestation_id",
    "review_attestation_url","review_signer_workflow",
    "ledger_mutation_permitted","readiness_mutation_permitted",
    "forecast_activation_permitted","ledger_record_proposal",
}
ALL_FIELDS=BODY_FIELDS|{"attested_decision_sha256"}

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def sign_attested_review_decision(body):
    result=dict(body)
    result["attested_decision_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return result

def verify_attested_review_decision(value):
    if not isinstance(value,dict) or set(value)!=ALL_FIELDS:
        return False
    if value.get("claim")!="live_auth_verified":
        return False
    if value.get("decision") not in {"APPROVE","REJECT"}:
        return False
    if not REVIEWER.fullmatch(value.get("reviewer","")):
        return False
    if not SHA64.fullmatch(value.get("candidate_sha256","")):
        return False
    if not SHA64.fullmatch(value.get("decision_sha256","")):
        return False
    if value.get("review_repository")!=SOURCE_REPOSITORY:
        return False
    if not RUN_ID.fullmatch(value.get("review_workflow_run_id","")):
        return False
    if not SHA40.fullmatch(value.get("review_source_commit","")):
        return False
    if value.get("review_github_metadata_match") is not True:
        return False
    if not SHA64.fullmatch(value.get("review_decision_file_sha256","")):
        return False
    if not SHA64.fullmatch(value.get("review_attestation_marker_sha256","")):
        return False
    if not isinstance(value.get("review_attestation_id"),str) or not value["review_attestation_id"]:
        return False
    if not isinstance(value.get("review_attestation_url"),str) or not value[
        "review_attestation_url"
    ].startswith("https://github.com/"+SOURCE_REPOSITORY+"/attestations/"):
        return False
    if value.get("review_signer_workflow")!=REVIEW_WORKFLOW:
        return False
    if value.get("ledger_mutation_permitted") is not False:
        return False
    if value.get("readiness_mutation_permitted") is not False:
        return False
    if value.get("forecast_activation_permitted") is not False:
        return False

    proposal=value.get("ledger_record_proposal")
    if value["decision"]=="REJECT":
        if value.get("attested_status")!="ATTESTED_REJECTED" or proposal is not None:
            return False
    else:
        if value.get("attested_status")!="ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW":
            return False
        if not isinstance(proposal,dict):
            return False
        required_review_fields={
            "review_repository","review_workflow_run_id","review_source_commit",
            "review_decision_sha256","review_decision_file_sha256",
            "review_attestation_marker_sha256","review_attestation_id",
            "review_attestation_url","review_signer_workflow",
            "review_github_metadata_match",
        }
        if not required_review_fields.issubset(proposal):
            return False
        if proposal.get("review_repository")!=value["review_repository"]:
            return False
        if proposal.get("review_workflow_run_id")!=value["review_workflow_run_id"]:
            return False
        if proposal.get("review_source_commit")!=value["review_source_commit"]:
            return False
        if proposal.get("review_decision_sha256")!=value["decision_sha256"]:
            return False
        if proposal.get("review_decision_file_sha256")!=value["review_decision_file_sha256"]:
            return False
        if proposal.get("review_attestation_marker_sha256")!=value["review_attestation_marker_sha256"]:
            return False
        if proposal.get("review_attestation_id")!=value["review_attestation_id"]:
            return False
        if proposal.get("review_attestation_url")!=value["review_attestation_url"]:
            return False
        if proposal.get("review_signer_workflow")!=value["review_signer_workflow"]:
            return False
        if proposal.get("review_github_metadata_match") is not True:
            return False

    expected=value.get("attested_decision_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:value[key] for key in BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)
