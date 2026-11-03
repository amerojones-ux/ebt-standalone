"""Strict ingestion of a signed live-auth promotion-preview artifact package."""
from datetime import datetime, timezone
import hashlib
import io
import json
import re
import stat
import zipfile

from provider_attested_review_decision import verify_attested_review_decision
from provider_promotion_preview_attestation_marker import (
    SOURCE_REPOSITORY,
    verify_promotion_preview_attestation_marker,
)

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
DIGEST=re.compile(r"^sha256:([0-9a-f]{64})$",re.I)
NAME=re.compile(r"^provider-live-auth-promotion-preview-([0-9]+)-([0-9]+)$")
MAX_ZIP_BYTES=1024*1024
MAX_FILE_BYTES=256*1024
EXPECTED_FILES={
    "provider_attested_review_decision.json",
    "provider_live_auth_promotion_preview.json",
    "provider_live_auth_promotion_preview_attestation_verification.json",
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

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")

def _validate_metadata(metadata, *, trusted_now):
    if not isinstance(metadata,dict):
        raise ValueError("promotion artifact metadata must be object")
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
        raise ValueError("invalid promotion artifact id")
    if type(size) is not int or size<=0 or size>MAX_ZIP_BYTES:
        raise ValueError("invalid promotion artifact size")
    if expired is not False:
        raise ValueError("promotion artifact expired")
    if now is None or created is None or expires is None:
        raise ValueError("promotion artifact timestamps invalid")
    if created>now or expires<=now or expires<=created:
        raise ValueError("promotion artifact time window invalid")
    digest_match=DIGEST.fullmatch(digest or "")
    if not digest_match:
        raise ValueError("invalid promotion artifact digest")
    if not isinstance(workflow,dict):
        raise ValueError("promotion workflow metadata required")

    run_id=workflow.get("id")
    run_attempt=workflow.get("run_attempt")
    repo_id=workflow.get("repository_id")
    head_repo_id=workflow.get("head_repository_id")
    branch=workflow.get("head_branch")
    commit=workflow.get("head_sha")
    if type(run_id) is not int or run_id<=0:
        raise ValueError("invalid promotion workflow run id")
    if type(run_attempt) is not int or run_attempt!=1:
        raise ValueError("promotion workflow run attempt must equal 1")
    if type(repo_id) is not int or repo_id<=0:
        raise ValueError("invalid promotion repository id")
    if type(head_repo_id) is not int or head_repo_id!=repo_id:
        raise ValueError("promotion head repository mismatch")
    if branch!="main":
        raise ValueError("promotion workflow must originate from main")
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        raise ValueError("invalid promotion workflow commit")

    name_match=NAME.fullmatch(name or "")
    if not name_match:
        raise ValueError("invalid promotion artifact name")
    review_run_id,artifact_run_id=name_match.groups()
    if artifact_run_id!=str(run_id):
        raise ValueError("promotion artifact name/run mismatch")

    return {
        "artifact_id":artifact_id,
        "artifact_digest":digest_match.group(1).lower(),
        "review_run_id":review_run_id,
        "promotion_run_id":str(run_id),
        "promotion_run_attempt":run_attempt,
        "promotion_commit":commit.lower(),
        "repository_id":repo_id,
    }

def ingest_promotion_preview_package(
    metadata,
    zip_bytes,
    *,
    repository,
    trusted_now,
):
    if repository!=SOURCE_REPOSITORY:
        raise ValueError("promotion package repository mismatch")
    binding=_validate_metadata(metadata,trusted_now=trusted_now)
    if not isinstance(zip_bytes,(bytes,bytearray)):
        raise ValueError("promotion artifact must be bytes")
    if len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("promotion artifact ZIP too large")
    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid promotion artifact ZIP") from exc

    raw_by_name={}
    with archive:
        members=archive.infolist()
        if len(members)!=3:
            raise ValueError("promotion artifact must contain exactly three files")
        names={info.filename for info in members}
        if names!=EXPECTED_FILES:
            raise ValueError("promotion artifact file set mismatch")
        for info in members:
            if info.is_dir():
                raise ValueError("promotion artifact member cannot be directory")
            if "/" in info.filename or "\\" in info.filename:
                raise ValueError("nested promotion artifact paths forbidden")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted promotion artifact member forbidden")
            if _is_symlink(info):
                raise ValueError("symlink promotion artifact member forbidden")
            if type(info.file_size) is not int or info.file_size<0 or info.file_size>MAX_FILE_BYTES:
                raise ValueError("promotion artifact member size invalid")
            with archive.open(info,"r") as handle:
                raw=handle.read(MAX_FILE_BYTES+1)
            if len(raw)>MAX_FILE_BYTES or len(raw)!=info.file_size:
                raise ValueError("promotion artifact member size mismatch")
            raw_by_name[info.filename]=raw

    parsed={}
    for name,raw in raw_by_name.items():
        try:
            parsed[name]=json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ValueError("promotion artifact JSON invalid") from exc

    decision=parsed["provider_attested_review_decision.json"]
    preview=parsed["provider_live_auth_promotion_preview.json"]
    marker=parsed[
        "provider_live_auth_promotion_preview_attestation_verification.json"
    ]

    if not verify_attested_review_decision(decision):
        raise ValueError("attested review decision invalid")
    if decision.get("decision")!="APPROVE":
        raise ValueError("promotion package decision not approved")
    if decision.get("review_workflow_run_id")!=binding["review_run_id"]:
        raise ValueError("promotion package review run mismatch")

    if not verify_promotion_preview_attestation_marker(
        marker,
        expected_run_id=binding["promotion_run_id"],
        expected_commit=binding["promotion_commit"],
        expected_review_run_id=binding["review_run_id"],
    ):
        raise ValueError("promotion preview attestation marker invalid")

    if not isinstance(preview,dict):
        raise ValueError("promotion preview must be object")
    if preview.get("preview_status")!="VALID_LIVE_AUTH_PROMOTION_PREVIEW":
        raise ValueError("promotion preview status invalid")
    if preview.get("global_provider_gate")!="SAFE_HOLD":
        raise ValueError("promotion preview crossed SAFE_HOLD")
    if preview.get("ledger_write_permitted") is not False:
        raise ValueError("promotion preview ledger write flag invalid")
    if preview.get("readiness_write_permitted") is not False:
        raise ValueError("promotion preview readiness write flag invalid")
    if preview.get("forecast_activation_permitted") is not False:
        raise ValueError("promotion preview forecast flag invalid")
    if preview.get("provider")!=decision.get("subject"):
        raise ValueError("promotion preview provider mismatch")
    if preview.get("claim")!="live_auth_verified":
        raise ValueError("promotion preview claim mismatch")
    if preview.get("decision_sha256")!=decision.get("decision_sha256"):
        raise ValueError("promotion preview decision mismatch")

    expected_preview_sha=preview.get("preview_sha256")
    if not isinstance(expected_preview_sha,str) or len(expected_preview_sha)!=64:
        raise ValueError("promotion preview checksum missing")
    preview_body={k:v for k,v in preview.items() if k!="preview_sha256"}
    actual_preview_sha=hashlib.sha256(_canonical(preview_body)).hexdigest()
    if actual_preview_sha!=expected_preview_sha:
        raise ValueError("promotion preview checksum invalid")
    if marker.get("preview_sha256")!=expected_preview_sha:
        raise ValueError("promotion marker preview checksum mismatch")

    preview_file_sha=hashlib.sha256(
        raw_by_name["provider_live_auth_promotion_preview.json"]
    ).hexdigest()
    if marker.get("preview_file_sha256")!=preview_file_sha:
        raise ValueError("promotion preview file checksum mismatch")

    return {
        "package_status":"VERIFIED_LIVE_AUTH_PROMOTION_PREVIEW_PACKAGE",
        "provider":preview["provider"],
        "claim":"live_auth_verified",
        "source_probe_run_id":marker["source_probe_run_id"],
        "review_run_id":binding["review_run_id"],
        "promotion_preview_run_id":binding["promotion_run_id"],
        "promotion_preview_commit":binding["promotion_commit"],
        "artifact_digest":binding["artifact_digest"],
        "preview_sha256":preview["preview_sha256"],
        "attested_review_decision":decision,
        "signed_preview":preview,
        "attestation_marker":marker,
    }
