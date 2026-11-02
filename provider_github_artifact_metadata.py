"""Validate GitHub Actions artifact metadata before receipt ingestion.

This module expects metadata obtained independently from GitHub's Actions artifact API.
It never performs network calls itself.
"""
from datetime import datetime, timezone
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
DIGEST=re.compile(r"^sha256:([0-9a-f]{64})$",re.I)

ARTIFACT_PREFIXES={
    "WeatherAPI":"weatherapi-probe-receipt-",
    "The Odds API":"theoddsapi-probe-receipt-",
    "API-Sports":"apisports-status-receipt-",
}
MAX_ARTIFACT_BYTES=1024*1024

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

def build_trusted_binding(metadata, *, provider, trusted_now):
    if provider not in ARTIFACT_PREFIXES:
        raise ValueError("unsupported provider")
    if not isinstance(metadata,dict):
        raise ValueError("artifact metadata must be object")

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
        raise ValueError("invalid artifact id")
    if type(size) is not int or size<=0 or size>MAX_ARTIFACT_BYTES:
        raise ValueError("invalid artifact size")
    if expired is not False:
        raise ValueError("artifact is expired")
    if now is None or created is None or expires is None:
        raise ValueError("artifact timestamps must be timezone-aware")
    if created>now:
        raise ValueError("artifact created_at cannot be in the future")
    if expires<=now:
        raise ValueError("artifact expiration has passed")
    if expires<=created:
        raise ValueError("artifact expiration must follow creation")

    if not isinstance(workflow,dict):
        raise ValueError("workflow_run metadata required")
    run_id=workflow.get("id")
    repo_id=workflow.get("repository_id")
    head_repo_id=workflow.get("head_repository_id")
    branch=workflow.get("head_branch")
    head_sha=workflow.get("head_sha")

    if type(run_id) is not int or run_id<=0:
        raise ValueError("invalid workflow run id")
    if type(repo_id) is not int or repo_id<=0:
        raise ValueError("invalid repository id")
    if type(head_repo_id) is not int or head_repo_id!=repo_id:
        raise ValueError("artifact head repository mismatch")
    if branch!="main":
        raise ValueError("artifact workflow must originate from main")
    if not isinstance(head_sha,str) or not SHA40.fullmatch(head_sha):
        raise ValueError("invalid workflow head sha")

    expected_name=ARTIFACT_PREFIXES[provider]+str(run_id)
    if name!=expected_name:
        raise ValueError("artifact name/run mismatch")

    match=DIGEST.fullmatch(digest or "")
    if not match:
        raise ValueError("invalid GitHub artifact digest")

    return {
        "provider":provider,
        "github_artifact_id":artifact_id,
        "github_artifact_name":name,
        "github_artifact_digest":match.group(1).lower(),
        "expected_run_id":str(run_id),
        "expected_commit":head_sha.lower(),
        "head_branch":"main",
        "metadata_binding_status":"GITHUB_ARTIFACT_METADATA_MATCH",
    }
