"""Strict ingestion of GitHub Actions attestation-verification marker ZIPs."""
import hashlib
import io
import json
import stat
import zipfile

from provider_attestation_verification_marker import verify_marker
from provider_github_artifact_metadata import build_attestation_marker_binding

MAX_ZIP_BYTES=1024*1024
MAX_MARKER_BYTES=65536

EXPECTED_FILES={
    "WeatherAPI":"weatherapi_attestation_verification.json",
    "The Odds API":"theoddsapi_attestation_verification.json",
    "API-Sports":"apisports_attestation_verification.json",
}

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def ingest_attestation_marker_artifact(
    metadata,
    zip_bytes,
    *,
    provider,
    repository,
    trusted_now,
):
    binding=build_attestation_marker_binding(
        metadata,provider=provider,trusted_now=trusted_now
    )

    if not isinstance(zip_bytes,(bytes,bytearray)):
        raise ValueError("marker artifact must be bytes")
    if len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("marker artifact ZIP too large")

    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid marker ZIP artifact") from exc

    with archive:
        members=archive.infolist()
        if len(members)!=1:
            raise ValueError("marker artifact must contain exactly one file")
        info=members[0]
        expected=EXPECTED_FILES[provider]

        if info.is_dir():
            raise ValueError("marker member cannot be directory")
        if info.filename!=expected:
            raise ValueError("unexpected marker filename")
        if "/" in info.filename or "\\" in info.filename:
            raise ValueError("nested marker paths are forbidden")
        if info.flag_bits & 0x1:
            raise ValueError("encrypted marker members are forbidden")
        if _is_symlink(info):
            raise ValueError("symlink marker members are forbidden")
        if type(info.file_size) is not int or info.file_size<0 or info.file_size>MAX_MARKER_BYTES:
            raise ValueError("marker file size invalid")

        try:
            with archive.open(info,"r") as handle:
                raw=handle.read(MAX_MARKER_BYTES+1)
        except (RuntimeError,zipfile.BadZipFile) as exc:
            raise ValueError("marker extraction failed") from exc

        if len(raw)>MAX_MARKER_BYTES:
            raise ValueError("marker file too large")
        if len(raw)!=info.file_size:
            raise ValueError("marker size mismatch")

    marker_file_sha256=hashlib.sha256(raw).hexdigest()
    try:
        marker=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("marker is not valid UTF-8 JSON") from exc

    if not verify_marker(
        marker,
        provider=provider,
        repository=repository,
        expected_run_id=binding["expected_run_id"],
        expected_commit=binding["expected_commit"],
    ):
        raise ValueError("attestation verification marker invalid")

    return {
        "status":"VERIFIED",
        "provider":provider,
        "binding":binding,
        "marker_filename":EXPECTED_FILES[provider],
        "marker_file_sha256":marker_file_sha256,
        "marker_internal_sha256":marker["marker_sha256"],
        "attestation_id":marker["attestation_id"],
        "attestation_url":marker["attestation_url"],
        "signer_workflow":marker["signer_workflow"],
    }
