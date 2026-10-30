"""Offline Ed25519 verification of weather release attestations.

This verifier checks a detached signature over caller-supplied canonical payload
bytes. Public keys must be independently pinned by the protected deployment.
It does not authenticate reviewers, check revocations or persist replay state.
It never grants production forecasting or wagering.
"""
from __future__ import annotations

import base64
import json
from collections.abc import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from extensions.weather_attestation_envelope import inspect_attestation_envelope


def verify_weather_attestation(
    *, payload: bytes, signature_b64: str, key_id: str,
    pinned_public_keys: Mapping[str, bytes],
    expected_repo: str, expected_commit: str,
    expected_environment: str, now_utc: str,
) -> dict[str, str]:
    blocked = {"signature": "NOT VERIFIED", "attestation": "BLOCKED",
               "forecast": "HOLD", "wager": "NOT APPROVED"}
    if (type(payload) is not bytes or not 0 < len(payload) <= 8192
            or type(signature_b64) is not str or len(signature_b64) > 128
            or type(key_id) is not str or not isinstance(pinned_public_keys, Mapping)):
        return blocked
    key_bytes = pinned_public_keys.get(key_id)
    if type(key_bytes) is not bytes or len(key_bytes) != 32:
        return blocked
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        if len(signature) != 64:
            return blocked
        document = json.loads(payload)
        if not isinstance(document, dict) or document.get("key_id") != key_id:
            return blocked
        # Prevent alternate JSON representations and duplicate-key confusion.
        canonical = json.dumps(document, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False).encode("ascii")
        if payload != canonical:
            return blocked
        structure = inspect_attestation_envelope(
            document, expected_repo=expected_repo,
            expected_commit=expected_commit,
            expected_environment=expected_environment, now_utc=now_utc)
        if structure["envelope"] != "STRUCTURALLY_VALID_ONLY":
            return blocked
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature, payload)
    except (ValueError, TypeError, UnicodeDecodeError, InvalidSignature):
        return blocked
    return {"signature": "CRYPTOGRAPHICALLY_VERIFIED",
            "attestation": "SIGNATURE_VALID_ONLY",
            "forecast": "HOLD", "wager": "NOT APPROVED"}
