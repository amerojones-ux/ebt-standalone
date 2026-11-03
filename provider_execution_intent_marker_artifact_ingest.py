"""Strict ingestion of execution-intent verification-marker artifacts."""
import hashlib
import io
import json
import stat
import zipfile

from provider_execution_intent_verification_marker import (
    verify_execution_intent_marker,
)
from provider_github_artifact_metadata import (
    build_execution_intent_marker_binding,
    verify_downloaded_artifact,
)

MAX_ZIP_BYTES=1024*1024
MAX_FILE_BYTES=65536
EXPECTED_FILES={
    "WeatherAPI":"weatherapi_execution_intent_attestation_verification.json",
    "The Odds API":"theoddsapi_execution_intent_attestation_verification.json",
    "API-Sports":"apisports_execution_intent_attestation_verification.json",
}

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def ingest_execution_intent_marker_artifact(
    metadata,
    zip_bytes,
    *,
    provider,
    trusted_now,
):
    binding=build_execution_intent_marker_binding(
        metadata,provider=provider,trusted_now=trusted_now
    )
    zip_sha256=verify_downloaded_artifact(binding,zip_bytes)
    if not isinstance(zip_bytes,(bytes,bytearray)) or len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("execution intent marker artifact invalid")
    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid execution intent marker ZIP") from exc
    with archive:
        members=archive.infolist()
        if len(members)!=1:
            raise ValueError("execution intent marker must contain one file")
        info=members[0]
        expected=EXPECTED_FILES[provider]
        if info.filename!=expected or info.is_dir():
            raise ValueError("unexpected execution intent marker filename")
        if "/" in info.filename or "\\" in info.filename:
            raise ValueError("nested execution intent marker path forbidden")
        if info.flag_bits & 0x1 or _is_symlink(info):
            raise ValueError("unsafe execution intent marker member")
        if type(info.file_size) is not int or info.file_size<=0 or info.file_size>MAX_FILE_BYTES:
            raise ValueError("execution intent marker size invalid")
        with archive.open(info,"r") as handle:
            raw=handle.read(MAX_FILE_BYTES+1)
        if len(raw)>MAX_FILE_BYTES or len(raw)!=info.file_size:
            raise ValueError("execution intent marker size mismatch")
    try:
        marker=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("execution intent marker invalid JSON") from exc
    if not verify_execution_intent_marker(
        marker,
        provider=provider,
        expected_run_id=binding["expected_run_id"],
        expected_commit=binding["expected_commit"],
    ):
        raise ValueError("execution intent marker verification failed")
    return {
        "status":"VERIFIED",
        "provider":provider,
        "binding":binding,
        "marker_zip_sha256":zip_sha256,
        "marker_file_sha256":hashlib.sha256(raw).hexdigest(),
        "marker_internal_sha256":marker["marker_sha256"],
        "intent_sha256":marker["intent_sha256"],
        "workflow_run_attempt":marker["workflow_run_attempt"],
        "intent_file_sha256":marker["intent_file_sha256"],
        "request_plan_sha256":marker["request_plan_sha256"],
        "actor":marker["actor"],
        "actor_id":marker["actor_id"],
        "max_requests":marker["max_requests"],
        "attestation_id":marker["attestation_id"],
        "attestation_url":marker["attestation_url"],
        "attestation_bundle_sha256":marker["attestation_bundle_sha256"],
        "signer_workflow":marker["signer_workflow"],
    }
