"""Reviewer decision layer for checksum-bound provider evidence candidates.

This module never edits the evidence ledger or readiness configuration.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
SHA64=re.compile(r"^[0-9a-f]{64}$",re.I)
RUN_REF=re.compile(r"^github-actions-run:[0-9]+$")
DECISIONS={"APPROVE","REJECT"}
SUPPORTED_PROVIDERS={"WeatherAPI","The Odds API","API-Sports"}
SOURCE_REPOSITORY="amerojones-ux/ebt-standalone"
SIGNER_WORKFLOWS={
    "WeatherAPI":".github/workflows/weatherapi-live-probe.yml",
    "The Odds API":".github/workflows/theoddsapi-live-probe.yml",
    "API-Sports":".github/workflows/apisports-status-probe.yml",
}

CANDIDATE_BODY_FIELDS={
    "provider","subject","claim","candidate_status","source_type","reference",
    "source_repository","source_commit","github_metadata_match",
    "receipt_sha256","artifact_sha256","attestation_verified",
    "attestation_marker_sha256","attestation_id","attestation_url",
    "signer_workflow","reviewer_required",
    "readiness_mutation_permitted","forecast_activation_permitted",
}
CANDIDATE_FIELDS=CANDIDATE_BODY_FIELDS|{"candidate_sha256"}

DECISION_BODY_FIELDS={
    "subject","claim","decision","reviewer","reviewed_at","candidate_sha256",
    "ledger_mutation_permitted","readiness_mutation_permitted",
    "forecast_activation_permitted","proposal_status","ledger_record_proposal",
}
DECISION_FIELDS=DECISION_BODY_FIELDS|{"decision_sha256"}

def _parse_time(value):
    if not isinstance(value,str) or not value.strip():
        return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt.astimezone(timezone.utc)

def _canonical(body):
    return json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")

def verify_candidate(candidate):
    if not isinstance(candidate,dict) or set(candidate)!=CANDIDATE_FIELDS:
        return False
    if candidate.get("provider") not in SUPPORTED_PROVIDERS:
        return False
    if candidate.get("provider")!=candidate.get("subject"):
        return False
    if candidate.get("claim")!="live_auth_verified":
        return False
    if candidate.get("candidate_status")!="REVIEW_ONLY":
        return False
    if candidate.get("source_type")!="github_actions_receipt":
        return False
    if not RUN_REF.fullmatch(candidate.get("reference","")):
        return False
    if candidate.get("source_repository")!=SOURCE_REPOSITORY:
        return False
    if not SHA40.fullmatch(candidate.get("source_commit","")):
        return False
    if candidate.get("github_metadata_match") is not True:
        return False
    if not SHA64.fullmatch(candidate.get("receipt_sha256","")):
        return False
    if not SHA64.fullmatch(candidate.get("artifact_sha256","")):
        return False
    if candidate.get("attestation_verified") is not True:
        return False
    if not SHA64.fullmatch(candidate.get("attestation_marker_sha256","")):
        return False
    if not isinstance(candidate.get("attestation_id"),str) or not candidate["attestation_id"]:
        return False
    if not isinstance(candidate.get("attestation_url"),str) or not candidate["attestation_url"].startswith(
        "https://github.com/"+SOURCE_REPOSITORY+"/attestations/"
    ):
        return False
    if candidate.get("signer_workflow")!=SIGNER_WORKFLOWS[candidate["provider"]]:
        return False
    if candidate.get("reviewer_required") is not True:
        return False
    if candidate.get("readiness_mutation_permitted") is not False:
        return False
    if candidate.get("forecast_activation_permitted") is not False:
        return False
    expected=candidate.get("candidate_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:candidate[key] for key in CANDIDATE_BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)

def _sign_decision(body):
    result=dict(body)
    result["decision_sha256"]=hashlib.sha256(_canonical(body)).hexdigest()
    return result

def verify_review_decision(result):
    if not isinstance(result,dict) or set(result)!=DECISION_FIELDS:
        return False
    if result.get("decision") not in DECISIONS:
        return False
    if result.get("claim")!="live_auth_verified":
        return False
    if result.get("subject") not in SUPPORTED_PROVIDERS:
        return False
    if not isinstance(result.get("reviewer"),str) or not result["reviewer"].strip():
        return False
    if _parse_time(result.get("reviewed_at")) is None:
        return False
    if not SHA64.fullmatch(result.get("candidate_sha256","")):
        return False
    if result.get("ledger_mutation_permitted") is not False:
        return False
    if result.get("readiness_mutation_permitted") is not False:
        return False
    if result.get("forecast_activation_permitted") is not False:
        return False

    proposal=result.get("ledger_record_proposal")
    if result.get("decision")=="REJECT":
        if result.get("proposal_status")!="REJECTED" or proposal is not None:
            return False
    else:
        if result.get("proposal_status")!="APPROVED_FOR_MANUAL_LEDGER_REVIEW":
            return False
        if not isinstance(proposal,dict):
            return False
        required={
            "status","subject","claim","source_type","reference","reviewed_at",
            "reviewer","source_repository","source_commit","receipt_sha256",
            "artifact_sha256","attestation_marker_sha256","attestation_id",
            "attestation_url","signer_workflow",
        }
        if set(proposal)!=required:
            return False
        if proposal.get("status")!="VERIFIED":
            return False
        if proposal.get("subject")!=result.get("subject"):
            return False
        if proposal.get("claim")!=result.get("claim"):
            return False
        if proposal.get("reviewer")!=result.get("reviewer"):
            return False
        if proposal.get("reviewed_at")!=result.get("reviewed_at"):
            return False
        if proposal.get("source_type")!="github_actions_receipt":
            return False
        if not RUN_REF.fullmatch(proposal.get("reference","")):
            return False
        if proposal.get("source_repository")!=SOURCE_REPOSITORY:
            return False
        if not SHA40.fullmatch(proposal.get("source_commit","")):
            return False
        if not SHA64.fullmatch(proposal.get("receipt_sha256","")):
            return False
        if not SHA64.fullmatch(proposal.get("artifact_sha256","")):
            return False
        if not SHA64.fullmatch(proposal.get("attestation_marker_sha256","")):
            return False
        if not isinstance(proposal.get("attestation_id"),str) or not proposal["attestation_id"]:
            return False
        if not isinstance(proposal.get("attestation_url"),str) or not proposal["attestation_url"].startswith(
            "https://github.com/"+SOURCE_REPOSITORY+"/attestations/"
        ):
            return False
        if proposal.get("signer_workflow")!=SIGNER_WORKFLOWS[proposal["subject"]]:
            return False

    expected=result.get("decision_sha256")
    if not isinstance(expected,str) or not SHA64.fullmatch(expected):
        return False
    body={key:result[key] for key in DECISION_BODY_FIELDS}
    actual=hashlib.sha256(_canonical(body)).hexdigest()
    return hmac.compare_digest(actual,expected)

def review_candidate(candidate, *, decision, reviewer, reviewed_at, trusted_now):
    if not verify_candidate(candidate):
        raise ValueError("candidate verification failed")
    if decision not in DECISIONS:
        raise ValueError("decision must be APPROVE or REJECT")
    if not isinstance(reviewer,str) or not reviewer.strip():
        raise ValueError("reviewer required")

    reviewed=_parse_time(reviewed_at)
    now=_parse_time(trusted_now)
    if reviewed is None or now is None:
        raise ValueError("timezone-aware review timestamps required")
    if reviewed > now:
        raise ValueError("reviewed_at cannot be in the future")

    body={
        "subject":candidate["subject"],
        "claim":candidate["claim"],
        "decision":decision,
        "reviewer":reviewer.strip(),
        "reviewed_at":reviewed_at,
        "candidate_sha256":candidate["candidate_sha256"],
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }

    if decision=="REJECT":
        body["proposal_status"]="REJECTED"
        body["ledger_record_proposal"]=None
        return _sign_decision(body)

    body["proposal_status"]="APPROVED_FOR_MANUAL_LEDGER_REVIEW"
    body["ledger_record_proposal"]={
        "status":"VERIFIED",
        "subject":candidate["subject"],
        "claim":candidate["claim"],
        "source_type":candidate["source_type"],
        "reference":candidate["reference"],
        "reviewed_at":reviewed_at,
        "reviewer":reviewer.strip(),
        "source_repository":candidate["source_repository"],
        "source_commit":candidate["source_commit"],
        "receipt_sha256":candidate["receipt_sha256"],
        "artifact_sha256":candidate["artifact_sha256"],
        "attestation_marker_sha256":candidate["attestation_marker_sha256"],
        "attestation_id":candidate["attestation_id"],
        "attestation_url":candidate["attestation_url"],
        "signer_workflow":candidate["signer_workflow"],
    }
    return _sign_decision(body)
