"""Independent weather integration release gate; no secrets or network operations.

Every requirement must be an explicit boolean True. The gate cannot infer
entitlements, model readiness, or deployment approval from successful CI/auth.
"""
from __future__ import annotations
from collections.abc import Mapping

REQUIREMENTS = (
    "protected_runner_reviewed",
    "egress_enforced",
    "credential_redaction_tested",
    "redirect_blocking_tested",
    "live_auth_verified",
    "subscription_rights_verified",
    "data_retention_rights_verified",
    "feed_schema_verified",
    "venue_time_join_verified",
    "no_lookahead_backtest_verified",
    "out_of_time_model_calibrated",
    "independent_release_approval",
)


def evaluate_weather_release(evidence: Mapping[str, object]) -> dict[str, object]:
    """Return an auditable fail-closed decision with no arbitrary input echoed."""
    if not isinstance(evidence, Mapping):
        evidence = {}
    missing = [name for name in REQUIREMENTS if evidence.get(name) is not True]
    approved = not missing
    return {
        "component": "weather",
        "integration_status": "APPROVED" if approved else "HOLD",
        "weather_feature_eligible": approved,
        # Separate platform-wide gates must independently authorize forecasts.
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
        "unmet_requirements": missing,
    }
