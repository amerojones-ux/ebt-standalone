"""Strict ingestion of persisted execution-intent Sigstore bundle artifacts."""
import hashlib
import io
import json
import stat
import zipfile

from provider_github_artifact_metadata import (
    build_execution_intent_bundle_binding,
    verify_downloaded_artifact,
)

MAX_ZIP_BYTES=1024*1024
MAX_BUNDLE_BYTES=1024*1024

EXPECTED_FILES={
    "WeatherAPI":"weatherapi_execution_intent_attestation_bundle.json",
    "The Odds API":"theoddsapi_execution_intent_attestation_bundle.json",
    "API-Sports":"apisports_execution_intent_attestation_bundle.json",
}

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def ingest_execution_intent_bundle_artifact(
    metadata,
    zip_bytes,
    *,
    provider,
    trusted_now,
    expected_bundle_sha256,
):
    binding=build_execution_intent_bundle_binding(
        metadata,provider=provider,trusted_now=trusted_now
    )
    bundle_zip_sha256=verify_downloaded_artifact(binding,zip_bytes)

    if (
        not isinstance(expected_bundle_sha256,str)
        or len(expected_bundle_sha256)!=64
        or any(ch not in "0123456789abcdefABCDEF" for ch in expected_bundle_sha256)
    ):
        raise ValueError("expected execution intent bundle SHA-256 required")
    if not isinstance(zip_bytes,(bytes,bytearray)):
        raise ValueError("execution intent bundle artifact must be bytes")
    if len(zip_bytes)>MAX_ZIP_BYTES:
        raise ValueError("execution intent bundle artifact ZIP too large")

    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid execution intent bundle ZIP artifact") from exc

    with archive:
        members=archive.infolist()
        if len(members)!=1:
            raise ValueError(
                "execution intent bundle artifact must contain exactly one file"
            )
        info=members[0]
        expected=EXPECTED_FILES[provider]
        if info.is_dir():
            raise ValueError("execution intent bundle member cannot be directory")
        if info.filename!=expected:
            raise ValueError("unexpected execution intent bundle filename")
        if "/" in info.filename or "\\" in info.filename:
            raise ValueError("nested execution intent bundle paths forbidden")
        if info.flag_bits & 0x1:
            raise ValueError("encrypted execution intent bundle forbidden")
        if _is_symlink(info):
            raise ValueError("execution intent bundle symlink forbidden")
        if (
            type(info.file_size) is not int
            or info.file_size<=0
            or info.file_size>MAX_BUNDLE_BYTES
        ):
            raise ValueError("execution intent bundle file size invalid")

        try:
            with archive.open(info,"r") as handle:
                raw=handle.read(MAX_BUNDLE_BYTES+1)
        except (RuntimeError,zipfile.BadZipFile) as exc:
            raise ValueError("execution intent bundle extraction failed") from exc

        if len(raw)>MAX_BUNDLE_BYTES:
            raise ValueError("execution intent bundle file too large")
        if len(raw)!=info.file_size:
            raise ValueError("execution intent bundle size mismatch")

    bundle_file_sha256=hashlib.sha256(raw).hexdigest()
    if bundle_file_sha256.lower()!=expected_bundle_sha256.lower():
        raise ValueError(
            "execution intent bundle file hash does not match verification marker"
        )

    try:
        parsed=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("execution intent bundle is not valid UTF-8 JSON") from exc
    if not isinstance(parsed,dict):
        raise ValueError("execution intent bundle JSON must be object")

    return {
        "status":"VERIFIED",
        "provider":provider,
        "binding":binding,
        "bundle_filename":EXPECTED_FILES[provider],
        "bundle_zip_sha256":bundle_zip_sha256,
        "bundle_file_sha256":bundle_file_sha256,
    }
