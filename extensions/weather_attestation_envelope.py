"""Fail-closed validation of a signed-attestation envelope's non-secret metadata.

This does NOT verify cryptographic signatures. It rejects malformed metadata
before a separate trusted verifier handles the signature and evidence provenance.
"""
from __future__ import annotations
import re
from collections.abc import Mapping
from datetime import datetime, timezone

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9_-]{8,96}$")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("invalid time")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone required")
    return t.astimezone(timezone.utc)


def inspect_attestation_envelope(
    envelope: Mapping[str, object], *, expected_repo: str,
    expected_commit: str, expected_environment: str,
    now_utc: str,
) -> dict[str, str]:
    """Never echo untrusted input; successful inspection remains NOT VERIFIED."""
    blocked = {"envelope": "BLOCKED", "signature": "NOT VERIFIED",
               "forecast": "HOLD", "wager": "NOT APPROVED"}
    if not isinstance(envelope, Mapping):
        return blocked
    try:
        issued = _time(envelope.get("issued_at"))
        expires = _time(envelope.get("expires_at"))
        now = _time(now_utc)
    except (ValueError, TypeError, OverflowError):
        return blocked
    valid = (
        envelope.get("schema_version") == "1"
        and type(expected_repo) is str and bool(expected_repo)
        and type(expected_commit) is str and bool(_HEX64.fullmatch(expected_commit))
        and type(expected_environment) is str and bool(expected_environment)
        and envelope.get("repository") == expected_repo
        and envelope.get("commit_sha") == expected_commit
        and envelope.get("environment") == expected_environment
        and envelope.get("decision") == "APPROVE"
        and type(envelope.get("evidence_digest")) is str
        and bool(_HEX64.fullmatch(envelope["evidence_digest"]))
        and type(envelope.get("nonce")) is str
        and bool(_ID.fullmatch(envelope["nonce"]))
        and type(envelope.get("issuer_id")) is str
        and bool(_ID.fullmatch(envelope["issuer_id"]))
        and type(envelope.get("key_id")) is str
        and bool(_ID.fullmatch(envelope["key_id"]))
        and issued <= now < expires
        and 0 < (expires - issued).total_seconds() <= 3600
    )
    if not valid:
        return blocked
    return {"envelope": "STRUCTURALLY_VALID_ONLY",
            "signature": "NOT VERIFIED", "forecast": "HOLD",
            "wager": "NOT APPROVED"}
