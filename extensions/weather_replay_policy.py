"""Fail-closed replay and revocation policy for verified attestation claims.

In-memory stores are strictly test doubles. A production implementation MUST
use an atomic, durable, shared nonce store and independently sourced revocations.
"""
from __future__ import annotations

from collections.abc import MutableSet
from extensions.weather_attestation_verify import verify_weather_attestation


def check_attestation_once(*, nonce: str, key_id: str, revoked_key_ids: frozenset[str],
                           used_nonces: MutableSet[str], signature_result: dict) -> dict[str, str]:
    blocked = {"attestation": "BLOCKED", "forecast": "HOLD",
               "wager": "NOT APPROVED"}
    if (type(nonce) is not str or not nonce.isascii() or not nonce.isalnum()
            or not 8 <= len(nonce) <= 96 or type(key_id) is not str
            or not isinstance(revoked_key_ids, frozenset)
            or not isinstance(used_nonces, MutableSet)
            or not isinstance(signature_result, dict)
            or signature_result.get("signature") != "CRYPTOGRAPHICALLY_VERIFIED"
            or signature_result.get("attestation") != "SIGNATURE_VALID_ONLY"
            or key_id in revoked_key_ids or nonce in used_nonces):
        return blocked
    # Only an in-process test double. Not atomic across workers; never a production gate.
    used_nonces.add(nonce)
    return {"attestation": "TEST_ONLY_NONCE_ACCEPTED",
            "forecast": "HOLD", "wager": "NOT APPROVED"}
