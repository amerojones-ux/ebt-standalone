"""Strict ingestion of signed execution-intent JSON artifacts."""
import hashlib
import io
import json
import stat
import zipfile

from provider_execution_intent import CONTRACTS, REPOSITORY, verify_execution_intent
from provider_github_artifact_metadata import (
    build_execution_intent_binding,
    verify_downloaded_artifact,
)

MAX_ZIP_BYTES=1024*1024
MAX_FILE_BYTES=65536
EXPECTED_FILE="provider_execution_intent.json"

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def ingest_execution_intent_artifact(
    metadata,
    zip_bytes,
    *,
    provider,
    trusted_now,
):
    binding=build_execution_intent_binding(
        metadata,provider=provider,trusted_now=trusted_now
    )
    zip_sha256=verify_downloaded_artifact(binding,zip_bytes)

    if not isinstance(zip_bytes,(bytes,bytearray)) or len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("execution intent artifact invalid")
    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid execution intent ZIP") from exc

    with archive:
        members=archive.infolist()
        if len(members)!=1:
            raise ValueError("execution intent artifact must contain exactly one file")
        info=members[0]
        if info.filename!=EXPECTED_FILE or info.is_dir():
            raise ValueError("unexpected execution intent filename")
        if "/" in info.filename or "\\" in info.filename:
            raise ValueError("nested execution intent path forbidden")
        if info.flag_bits & 0x1 or _is_symlink(info):
            raise ValueError("unsafe execution intent ZIP member")
        if type(info.file_size) is not int or info.file_size<=0 or info.file_size>MAX_FILE_BYTES:
            raise ValueError("execution intent file size invalid")
        with archive.open(info,"r") as handle:
            raw=handle.read(MAX_FILE_BYTES+1)
        if len(raw)>MAX_FILE_BYTES or len(raw)!=info.file_size:
            raise ValueError("execution intent file size mismatch")

    try:
        intent=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("execution intent is not valid JSON") from exc
    if not verify_execution_intent(intent):
        raise ValueError("execution intent contract invalid")
    contract=CONTRACTS[provider]
    if intent.get("provider")!=provider:
        raise ValueError("execution intent provider mismatch")
    if intent.get("repository")!=REPOSITORY:
        raise ValueError("execution intent repository mismatch")
    if intent.get("workflow_run_id")!=binding["expected_run_id"]:
        raise ValueError("execution intent run mismatch")
    if intent.get("source_commit")!=binding["expected_commit"]:
        raise ValueError("execution intent commit mismatch")
    if intent.get("signer_workflow")!=contract["workflow"]:
        raise ValueError("execution intent workflow mismatch")

    return {
        "status":"VERIFIED",
        "provider":provider,
        "binding":binding,
        "intent_zip_sha256":zip_sha256,
        "intent_file_sha256":hashlib.sha256(raw).hexdigest(),
        "intent_sha256":intent["intent_sha256"],
        "workflow_run_attempt":intent["workflow_run_attempt"],
        "request_plan_sha256":intent["request_plan_sha256"],
        "actor":intent["actor"],
        "actor_id":intent["actor_id"],
        "max_requests":intent["max_requests"],
    }
