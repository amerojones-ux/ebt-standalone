"""External verification boundary for weather release evidence.

Offline reviewer metadata is untrusted. Only a separately verified assertion
from an approved authority can satisfy an evidence requirement. This module
does not fetch evidence, verify signatures, or grant deployment permissions.
"""
from __future__ import annotations

from collections.abc import Mapping
from extensions.weather_release_audit import OWNER
from extensions.weather_release_gate import REQUIREMENTS, evaluate_weather_release


def evaluate_verified_weather_evidence(
    assertions: Mapping[str, object],
    *, trusted_authorities: frozenset[str],
) -> dict[str, object]:
    """Require one unique externally verified assertion per release requirement."""
    if not isinstance(assertions, Mapping):
        assertions = {}
    if not isinstance(trusted_authorities, frozenset):
        trusted_authorities = frozenset()
    passed = {}
    used = set()
    for name in REQUIREMENTS:
        entry = assertions.get(name)
        if not isinstance(entry, Mapping):
            passed[name] = False
            continue
        identifier = entry.get("assertion_id")
        authority = entry.get("authority")
        verified = entry.get("externally_verified") is True
        role = entry.get("reviewer_role")
        acceptable = (verified and type(identifier) is str
                      and 8 <= len(identifier) <= 96
                      and identifier.isascii() and identifier.isalnum()
                      and identifier not in used
                      and type(authority) is str and authority in trusted_authorities
                      and role == OWNER[name])
        passed[name] = acceptable
        if acceptable:
            used.add(identifier)
    decision = evaluate_weather_release(passed)
    return {**decision,
            "verification_boundary": "CALLER_ASSERTED_EXTERNAL_VERIFICATION",
            "note": "This function cannot authenticate its caller or independently verify assertions; do not use as a production authorization boundary."}
