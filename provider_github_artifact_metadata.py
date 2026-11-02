"""Validate GitHub Actions artifact metadata before evidence ingestion.

This module expects metadata obtained independently from GitHub's Actions artifact API.
It never performs network calls itself.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import re

SHA40=re.compile(r"^[0-9a-f]{40}$",re.I)
DIGEST=re.compile(r"^sha256:([0-9a-f]{64})$",re.I)

RECEIPT_PREFIXES={
    "WeatherAPI":"weatherapi-probe-receipt-",
    "The Odds API":"theoddsapi-probe-receipt-",
    "API-Sports":"apisports-status-receipt-",
}
ATTESTATION_MARKER_PREFIXES={
    "WeatherAPI":"weatherapi-attestation-verification-",
    "The Odds API":"theoddsapi-attestation-verification-",
    "API-Sports":"apisports-attestation-verification-",
}
ATTESTATION_BUNDLE_PREFIXES={
    "WeatherAPI":"weatherapi-attestation-bundle-",
    "The Odds API":"theoddsapi-attestation-bundle-",
    "API-Sports":"apisports-attestation-bundle-",
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

def _build_binding(metadata, *, provider, trusted_now, prefixes, kind):
    if provider not in prefixes:
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

    expected_name=prefixes[provider]+str(run_id)
    if name!=expected_name:
        raise ValueError("artifact name/run mismatch")

    match=DIGEST.fullmatch(digest or "")
    if not match:
        raise ValueError("invalid GitHub artifact digest")

    return {
        "provider":provider,
        "artifact_kind":kind,
        "github_artifact_id":artifact_id,
        "github_artifact_name":name,
        "github_artifact_size":size,
        "github_artifact_digest":match.group(1).lower(),
        "expected_run_id":str(run_id),
        "expected_commit":head_sha.lower(),
        "head_branch":"main",
        "repository_id":repo_id,
        "metadata_binding_status":"GITHUB_ARTIFACT_METADATA_MATCH",
    }

def build_trusted_binding(metadata, *, provider, trusted_now):
    return _build_binding(
        metadata,provider=provider,trusted_now=trusted_now,
        prefixes=RECEIPT_PREFIXES,kind="receipt"
    )

def build_attestation_marker_binding(metadata, *, provider, trusted_now):
    return _build_binding(
        metadata,provider=provider,trusted_now=trusted_now,
        prefixes=ATTESTATION_MARKER_PREFIXES,kind="attestation_verification_marker"
    )

def build_attestation_bundle_binding(metadata, *, provider, trusted_now):
    return _build_binding(
        metadata,provider=provider,trusted_now=trusted_now,
        prefixes=ATTESTATION_BUNDLE_PREFIXES,kind="attestation_bundle"
    )


def verify_downloaded_artifact(binding, data):
    """Bind downloaded ZIP bytes to GitHub artifact metadata."""
    if not isinstance(binding,dict):
        raise ValueError("artifact binding must be object")
    if not isinstance(data,(bytes,bytearray)):
        raise ValueError("downloaded artifact must be bytes")

    expected_size=binding.get("github_artifact_size")
    if type(expected_size) is not int or expected_size<=0:
        raise ValueError("invalid expected artifact size")
    if len(data)!=expected_size:
        raise ValueError("downloaded artifact size mismatch")

    expected_digest=binding.get("github_artifact_digest")
    if not isinstance(expected_digest,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_digest,re.I):
        raise ValueError("invalid expected artifact digest")

    actual=hashlib.sha256(bytes(data)).hexdigest()
    if not hmac.compare_digest(actual,expected_digest.lower()):
        raise ValueError("downloaded artifact digest mismatch")
    return actual
