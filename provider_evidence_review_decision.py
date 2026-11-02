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

CANDIDATE_BODY_FIELDS={
    "provider","subject","claim","candidate_status","source_type","reference",
    "source_commit","artifact_sha256","reviewer_required",
    "readiness_mutation_permitted","forecast_activation_permitted",
}
CANDIDATE_FIELDS=CANDIDATE_BODY_FIELDS|{"candidate_sha256"}

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
    if not SHA40.fullmatch(candidate.get("source_commit","")):
        return False
    if not SHA64.fullmatch(candidate.get("artifact_sha256","")):
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

    result={
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
        result["proposal_status"]="REJECTED"
        result["ledger_record_proposal"]=None
        return result

    result["proposal_status"]="APPROVED_FOR_MANUAL_LEDGER_REVIEW"
    result["ledger_record_proposal"]={
        "status":"VERIFIED",
        "subject":candidate["subject"],
        "claim":candidate["claim"],
        "source_type":candidate["source_type"],
        "reference":candidate["reference"],
        "reviewed_at":reviewed_at,
        "reviewer":reviewer.strip(),
        "source_commit":candidate["source_commit"],
        "artifact_sha256":candidate["artifact_sha256"],
    }
    return result
