"""Offline integrity checks for immutable, redacted provider capture records.

A matching digest detects mutation; it does NOT authenticate a provider or establish
independent official reconciliation. External trusted provenance remains mandatory.
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class CaptureRecord:
    provider: str
    endpoint_id: str
    retrieved_at: str
    source_published_at: str
    payload: Mapping[str, Any]
    sha256: str

def canonical_digest(payload: Mapping[str, Any]) -> str:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be mapping")
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def verify_integrity(record: CaptureRecord | None) -> tuple[str, str]:
    if record is None:
        return ("NOT_TESTED", "NO_CAPTURE")
    if not record.provider or not record.endpoint_id:
        return ("FAIL", "MISSING_SOURCE_IDENTITY")
    if not record.retrieved_at or not record.source_published_at:
        return ("HOLD", "TIMESTAMPS_MISSING")
    try:
        expected = canonical_digest(record.payload)
    except (TypeError, ValueError):
        return ("FAIL", "INVALID_CANONICAL_PAYLOAD")
    if len(record.sha256) != 64 or not hashlib.compare_digest(record.sha256, expected):
        return ("FAIL", "CAPTURE_DIGEST_MISMATCH")
    return ("PASS", "CAPTURE_INTEGRITY_ONLY")
