"""Audit weather release evidence without logging raw source values or secrets.

This is an offline integrity gate, not a cryptographic signature verifier.
Evidence IDs are non-secret opaque references to separately retained reviews.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from extensions.weather_release_gate import REQUIREMENTS, evaluate_weather_release

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,95}$")
REVIEWERS = frozenset({"security", "data_rights", "model_validation", "release_manager"})
OWNER = {
    "protected_runner_reviewed": "security",
    "egress_enforced": "security",
    "credential_redaction_tested": "security",
    "redirect_blocking_tested": "security",
    "live_auth_verified": "security",
    "subscription_rights_verified": "data_rights",
    "data_retention_rights_verified": "data_rights",
    "feed_schema_verified": "data_rights",
    "venue_time_join_verified": "model_validation",
    "no_lookahead_backtest_verified": "model_validation",
    "out_of_time_model_calibrated": "model_validation",
    "independent_release_approval": "release_manager",
}


def audit_weather_release(records: Mapping[str, object]) -> dict[str, object]:
    """Require explicit, attributable evidence references for every gate."""
    verified = {}
    issues = []
    if not isinstance(records, Mapping):
        records = {}
    seen = set()
    for name in REQUIREMENTS:
        entry = records.get(name)
        if not isinstance(entry, Mapping):
            issues.append(name)
            verified[name] = False
            continue
        reviewer = entry.get("reviewer_role")
        ref = entry.get("evidence_id")
        passed = entry.get("passed") is True
        acceptable = (passed and reviewer in REVIEWERS and reviewer == OWNER[name]
                      and isinstance(ref, str) and bool(_ID.fullmatch(ref))
                      and ref not in seen)
        if acceptable:
            seen.add(ref)
        else:
            issues.append(name)
        verified[name] = acceptable
    result = evaluate_weather_release(verified)
    return {**result, "audit_status": "COMPLETE" if not issues else "INCOMPLETE",
            "unverified_evidence": issues,
            "note": "Evidence references require external verification; this offline check cannot establish authenticity."}
