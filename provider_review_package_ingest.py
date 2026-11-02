"""Strict ingestion of the GitHub live-auth review package artifact."""
from datetime import datetime, timezone
import copy
import hashlib
import io
import json
import re
import stat
import zipfile

from provider_attested_review_decision import sign_attested_review_decision
from provider_evidence_review_decision import (
    verify_candidate,
    verify_review_decision,
)
from provider_review_attestation_marker import (
    REVIEW_WORKFLOW,
    SOURCE_REPOSITORY,
    verify_review_attestation_marker,
)

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
DIGEST=re.compile(r"^sha256:([0-9a-f]{64})$",re.I)
NAME=re.compile(r"^provider-live-auth-review-([0-9]+)-([0-9]+)$")
MAX_ZIP_BYTES=1024*1024
MAX_FILE_BYTES=65536
EXPECTED_FILES={
    "provider_review_candidate.json",
    "provider_review_decision.json",
    "provider_review_decision_attestation_verification.json",
}

def _parse_time(value):
    if not isinstance(value,str) or not value.strip():
        return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def _validate_metadata(metadata, *, trusted_now):
    if not isinstance(metadata,dict):
        raise ValueError("review artifact metadata must be object")
    artifact_id=metadata.get("id")
    size=metadata.get("size_in_bytes")
    expired=metadata.get("expired")
    name=metadata.get("name")
    digest=metadata.get("digest")
    created=_parse_time(metadata.get("created_at"))
    expires=_parse_time(metadata.get("expires_at"))
    now=_parse_time(trusted_now)
    workflow=metadata.get("workflow_run")

    if type(artifact_id) is not int or artifact_id<=0:
        raise ValueError("invalid review artifact id")
    if type(size) is not int or size<=0 or size>MAX_ZIP_BYTES:
        raise ValueError("invalid review artifact size")
    if expired is not False:
        raise ValueError("review artifact expired")
    if now is None or created is None or expires is None:
        raise ValueError("review artifact timestamps invalid")
    if created>now or expires<=now or expires<=created:
        raise ValueError("review artifact time window invalid")
    match=DIGEST.fullmatch(digest or "")
    if not match:
        raise ValueError("invalid review artifact digest")
    if not isinstance(workflow,dict):
        raise ValueError("review workflow metadata required")
    run_id=workflow.get("id")
    repo_id=workflow.get("repository_id")
    head_repo_id=workflow.get("head_repository_id")
    branch=workflow.get("head_branch")
    commit=workflow.get("head_sha")
    if type(run_id) is not int or run_id<=0:
        raise ValueError("invalid review workflow run id")
    if type(repo_id) is not int or repo_id<=0:
        raise ValueError("invalid review repository id")
    if type(head_repo_id) is not int or head_repo_id!=repo_id:
        raise ValueError("review head repository mismatch")
    if branch!="main":
        raise ValueError("review workflow must originate from main")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        raise ValueError("invalid review workflow commit")
    name_match=NAME.fullmatch(name or "")
    if not name_match:
        raise ValueError("invalid review artifact name")
    source_run_id,artifact_review_run_id=name_match.groups()
    if artifact_review_run_id!=str(run_id):
        raise ValueError("review artifact name/run mismatch")
    return {
        "artifact_id":artifact_id,
        "artifact_digest":match.group(1).lower(),
        "source_run_id":source_run_id,
        "review_run_id":str(run_id),
        "review_commit":commit.lower(),
        "repository_id":repo_id,
    }

def ingest_review_package(metadata, zip_bytes, *, repository, trusted_now):
    if repository != SOURCE_REPOSITORY:
        raise ValueError("review package repository mismatch")
    binding=_validate_metadata(metadata,trusted_now=trusted_now)
    if not isinstance(zip_bytes,(bytes,bytearray)):
        raise ValueError("review artifact must be bytes")
    if len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("review artifact ZIP too large")
    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid review artifact ZIP") from exc

    raw_by_name={}
    with archive:
        members=archive.infolist()
        if len(members)!=3:
            raise ValueError("review artifact must contain exactly three files")
        names={info.filename for info in members}
        if names!=EXPECTED_FILES:
            raise ValueError("review artifact file set mismatch")
        for info in members:
            if info.is_dir():
                raise ValueError("review artifact member cannot be directory")
            if "/" in info.filename or "\\" in info.filename:
                raise ValueError("nested review artifact paths forbidden")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted review artifact member forbidden")
            if _is_symlink(info):
                raise ValueError("symlink review artifact member forbidden")
            if type(info.file_size) is not int or info.file_size<0 or info.file_size>MAX_FILE_BYTES:
                raise ValueError("review artifact member size invalid")
            with archive.open(info,"r") as handle:
                raw=handle.read(MAX_FILE_BYTES+1)
            if len(raw)>MAX_FILE_BYTES or len(raw)!=info.file_size:
                raise ValueError("review artifact member size mismatch")
            raw_by_name[info.filename]=raw

    parsed={}
    for name,raw in raw_by_name.items():
        try:
            parsed[name]=json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ValueError("review artifact JSON invalid") from exc

    candidate=parsed["provider_review_candidate.json"]
    decision=parsed["provider_review_decision.json"]
    marker=parsed["provider_review_decision_attestation_verification.json"]

    if not verify_candidate(candidate):
        raise ValueError("review candidate invalid")
    if not verify_review_decision(decision):
        raise ValueError("review decision invalid")
    if decision.get("candidate_sha256")!=candidate.get("candidate_sha256"):
        raise ValueError("candidate/decision checksum mismatch")
    if decision.get("reviewer")!=marker.get("reviewer"):
        raise ValueError("reviewer/marker mismatch")

    source_ref=candidate.get("reference","")
    expected_source="github-actions-run:"+binding["source_run_id"]
    if source_ref!=expected_source:
        raise ValueError("source probe run mismatch")

    if not verify_review_attestation_marker(
        marker,
        expected_run_id=binding["review_run_id"],
        expected_commit=binding["review_commit"],
    ):
        raise ValueError("review attestation marker invalid")

    decision_file_sha=hashlib.sha256(
        raw_by_name["provider_review_decision.json"]
    ).hexdigest()
    marker_file_sha=hashlib.sha256(
        raw_by_name["provider_review_decision_attestation_verification.json"]
    ).hexdigest()

    proposal=decision.get("ledger_record_proposal")
    final_proposal=None
    if decision.get("decision")=="APPROVE":
        if not isinstance(proposal,dict):
            raise ValueError("approved decision missing ledger proposal")
        final_proposal=copy.deepcopy(proposal)
        final_proposal.update({
            "review_repository":SOURCE_REPOSITORY,
            "review_workflow_run_id":binding["review_run_id"],
            "review_source_commit":binding["review_commit"],
            "review_github_metadata_match":True,
            "review_decision_sha256":decision["decision_sha256"],
            "review_decision_file_sha256":decision_file_sha,
            "review_attestation_marker_sha256":marker_file_sha,
            "review_attestation_id":marker["attestation_id"],
            "review_attestation_url":marker["attestation_url"],
            "review_signer_workflow":REVIEW_WORKFLOW,
        })
        attested_status="ATTESTED_APPROVED_FOR_MANUAL_LEDGER_REVIEW"
    else:
        if proposal is not None:
            raise ValueError("rejected decision cannot have ledger proposal")
        attested_status="ATTESTED_REJECTED"

    body={
        "subject":decision["subject"],
        "claim":decision["claim"],
        "decision":decision["decision"],
        "reviewer":decision["reviewer"],
        "reviewed_at":decision["reviewed_at"],
        "candidate_sha256":decision["candidate_sha256"],
        "decision_sha256":decision["decision_sha256"],
        "attested_status":attested_status,
        "review_repository":SOURCE_REPOSITORY,
        "review_workflow_run_id":binding["review_run_id"],
        "review_source_commit":binding["review_commit"],
        "review_github_metadata_match":True,
        "review_decision_file_sha256":decision_file_sha,
        "review_attestation_marker_sha256":marker_file_sha,
        "review_attestation_id":marker["attestation_id"],
        "review_attestation_url":marker["attestation_url"],
        "review_signer_workflow":REVIEW_WORKFLOW,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
        "ledger_record_proposal":final_proposal,
    }
    return sign_attested_review_decision(body)
