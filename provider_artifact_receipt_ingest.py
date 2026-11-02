"""Strict ingestion of GitHub Actions sanitized provider receipt ZIP artifacts.

No network, secret, ledger, readiness, or forecast mutation.
"""
import hashlib
import io
import json
import stat
import zipfile

from provider_receipt_review_candidate import build_review_candidate

MAX_ZIP_BYTES=1024*1024
MAX_RECEIPT_BYTES=65536

EXPECTED_FILES={
    "WeatherAPI":"weatherapi_probe_receipt.json",
    "The Odds API":"theoddsapi_probe_receipt.json",
    "API-Sports":"apisports_status_receipt.json",
}

def _is_symlink(info):
    mode=(info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def ingest_artifact_bytes(data, *, provider):
    if provider not in EXPECTED_FILES:
        raise ValueError("unsupported provider")
    if not isinstance(data,(bytes,bytearray)):
        raise ValueError("artifact must be bytes")
    if len(data)>MAX_ZIP_BYTES:
        raise ValueError("artifact ZIP too large")

    try:
        archive=zipfile.ZipFile(io.BytesIO(bytes(data)),"r")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid ZIP artifact") from exc

    with archive:
        members=archive.infolist()
        if len(members)!=1:
            raise ValueError("artifact must contain exactly one file")
        info=members[0]
        expected=EXPECTED_FILES[provider]

        if info.is_dir():
            raise ValueError("artifact member cannot be directory")
        if info.filename!=expected:
            raise ValueError("unexpected receipt filename")
        if "/" in info.filename or "\\" in info.filename:
            raise ValueError("nested receipt paths are forbidden")
        if info.flag_bits & 0x1:
            raise ValueError("encrypted ZIP members are forbidden")
        if _is_symlink(info):
            raise ValueError("symlink ZIP members are forbidden")
        if type(info.file_size) is not int or info.file_size<0 or info.file_size>MAX_RECEIPT_BYTES:
            raise ValueError("receipt file size invalid")

        try:
            with archive.open(info,"r") as handle:
                raw=handle.read(MAX_RECEIPT_BYTES+1)
        except (RuntimeError,zipfile.BadZipFile) as exc:
            raise ValueError("receipt extraction failed") from exc

        if len(raw)>MAX_RECEIPT_BYTES:
            raise ValueError("receipt file too large")
        if len(raw)!=info.file_size:
            raise ValueError("receipt size mismatch")

    artifact_sha256=hashlib.sha256(raw).hexdigest()
    try:
        receipt=json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:
        raise ValueError("receipt is not valid UTF-8 JSON") from exc

    candidate=build_review_candidate(
        receipt,
        artifact_sha256=artifact_sha256,
    )
    if candidate["provider"]!=provider:
        raise ValueError("provider/receipt mismatch")

    return {
        "ingestion_status":"REVIEW_ONLY",
        "provider":provider,
        "receipt_filename":EXPECTED_FILES[provider],
        "receipt_file_sha256":artifact_sha256,
        "receipt_internal_sha256":receipt["receipt_sha256"],
        "candidate":candidate,
        "ledger_mutation_permitted":False,
        "readiness_mutation_permitted":False,
        "forecast_activation_permitted":False,
    }
