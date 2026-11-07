"""Policy-driven calibration certification review for Black Diamond.

This module wraps the existing temporal isotonic calibration assessment with
predeclared market-specific acceptance limits. It can make a calibration package
eligible for human certification review, but never sets calibration_verified=True
or promotes a live model.

A separate candidate diagnostic uses the fitted isotonic block plus a Jeffreys
Beta posterior to expose local probability uncertainty. That diagnostic is not
a calibration certificate.
"""
from bisect import bisect_left
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import random
import re
from typing import Any, Dict, Mapping

from ebt_calibration import assessment, compile_blocks
from ebt_validation import exact_probability
from .underperformance import num

SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{field} lowercase SHA-256 required")
    return value


def _unit_interval(value: Any, field: str) -> Decimal:
    x = num(value)
    if not Decimal(0) <= x <= Decimal(1):
        raise ValueError(f"{field} must be in [0,1]")
    return x


def _acceptance_policy(raw: Mapping[str, Any], fit_at: str):
    required = {
        "policy_id", "declared_at",
        "max_validation_brier",
        "max_validation_expected_calibration_error",
        "max_validation_max_calibration_gap",
        "minimum_calibration_block_count",
        "require_calibrated_brier_not_worse_than_raw",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("exact calibration acceptance policy schema required")
    if not isinstance(raw["policy_id"], str) or not raw["policy_id"].strip():
        raise ValueError("policy_id required")
    declared = _clock(raw["declared_at"], "acceptance_policy.declared_at")
    fit = _clock(fit_at, "fit_at")
    thresholds = {
        "max_validation_brier": _unit_interval(
            raw["max_validation_brier"], "max_validation_brier"),
        "max_validation_expected_calibration_error": _unit_interval(
            raw["max_validation_expected_calibration_error"],
            "max_validation_expected_calibration_error"),
        "max_validation_max_calibration_gap": _unit_interval(
            raw["max_validation_max_calibration_gap"],
            "max_validation_max_calibration_gap"),
    }
    block_count = raw["minimum_calibration_block_count"]
    if type(block_count) is not int or block_count <= 0:
        raise ValueError("minimum_calibration_block_count must be positive integer")
    if type(raw["require_calibrated_brier_not_worse_than_raw"]) is not bool:
        raise ValueError("require_calibrated_brier_not_worse_than_raw boolean required")
    return {
        "policy_id": raw["policy_id"].strip(),
        "declared_at": declared,
        **thresholds,
        "minimum_calibration_block_count": block_count,
        "require_calibrated_brier_not_worse_than_raw":
            raw["require_calibrated_brier_not_worse_than_raw"],
        "predeclared_before_fit": declared < fit,
    }


def _reliability_metrics(rows):
    if not isinstance(rows, list):
        raise ValueError("reliability rows required")
    total = sum(row.get("count", 0) for row in rows)
    if total <= 0:
        raise ValueError("nonempty reliability sample required")
    weighted = 0.0
    max_gap = 0.0
    for row in rows:
        count = row.get("count")
        mean_p = row.get("mean_p")
        hit_rate = row.get("hit_rate")
        if type(count) is not int or count < 0:
            raise ValueError("invalid reliability count")
        if count == 0:
            continue
        if not isinstance(mean_p, (int, float)) or not isinstance(hit_rate, (int, float)):
            raise ValueError("reliability probability/rate required")
        gap = abs(float(mean_p) - float(hit_rate))
        weighted += (count / total) * gap
        max_gap = max(max_gap, gap)
    return {
        "expected_calibration_error": weighted,
        "max_calibration_gap": max_gap,
        "n": total,
    }


def _canonical_hash(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False,
            default=str,
        ).encode()
    ).hexdigest()


def assess_calibration_certification_review(
    training,
    validation,
    *,
    scope,
    fit_at,
    assessed_at,
    research_policy,
    acceptance_policy,
):
    """Assess a real calibration package for human certification review."""
    policy = _acceptance_policy(acceptance_policy, fit_at)
    base = assessment(
        training,
        validation,
        scope=scope,
        fit_at=fit_at,
        assessed_at=assessed_at,
        policy=research_policy,
    )
    reasons = []
    if not policy["predeclared_before_fit"]:
        reasons.append("ACCEPTANCE_POLICY_NOT_PREDECLARED_BEFORE_FIT")

    training_sha = _canonical_hash(training)
    validation_sha = _canonical_hash(validation)
    if base.get("status") != "RESEARCH_FIT_EVALUATED":
        reasons.append("UNDERLYING_CALIBRATION_ASSESSMENT_HOLD")

    metrics = None
    block_min_count = None
    map_sha = None
    blocks = base.get("blocks")
    if base.get("status") == "RESEARCH_FIT_EVALUATED":
        metrics = _reliability_metrics(base["reliability_calibrated"])
        calibrated_brier = base["heldout_calibrated"]["brier"]
        raw_brier = base["heldout_raw"]["brier"]
        if calibrated_brier > float(policy["max_validation_brier"]):
            reasons.append("VALIDATION_BRIER_EXCEEDS_POLICY")
        if (
            metrics["expected_calibration_error"]
            > float(policy["max_validation_expected_calibration_error"])
        ):
            reasons.append("VALIDATION_ECE_EXCEEDS_POLICY")
        if (
            metrics["max_calibration_gap"]
            > float(policy["max_validation_max_calibration_gap"])
        ):
            reasons.append("VALIDATION_MAX_GAP_EXCEEDS_POLICY")
        if (
            policy["require_calibrated_brier_not_worse_than_raw"]
            and calibrated_brier > raw_brier
        ):
            reasons.append("CALIBRATED_BRIER_WORSE_THAN_RAW")
        block_min_count = min(block["count"] for block in blocks)
        if block_min_count < policy["minimum_calibration_block_count"]:
            reasons.append("CALIBRATION_BLOCK_SAMPLE_BELOW_POLICY")
        map_sha = _canonical_hash(blocks)

    eligible = not reasons
    policy_out = {
        "policy_id": policy["policy_id"],
        "declared_at": policy["declared_at"].isoformat(),
        "max_validation_brier": str(policy["max_validation_brier"]),
        "max_validation_expected_calibration_error": str(
            policy["max_validation_expected_calibration_error"]),
        "max_validation_max_calibration_gap": str(
            policy["max_validation_max_calibration_gap"]),
        "minimum_calibration_block_count": policy["minimum_calibration_block_count"],
        "require_calibrated_brier_not_worse_than_raw":
            policy["require_calibrated_brier_not_worse_than_raw"],
        "predeclared_before_fit": policy["predeclared_before_fit"],
    }
    review_body = {
        "scope": scope,
        "fit_at": fit_at,
        "assessed_at": assessed_at,
        "research_policy": research_policy,
        "acceptance_policy": policy_out,
        "underlying_assessment_status": base.get("status"),
        "counts": base.get("counts"),
        "training_sha256": training_sha,
        "validation_sha256": validation_sha,
        "calibration_map_sha256": map_sha,
        "calibration_blocks": blocks,
        "validation_calibrated": base.get("heldout_calibrated"),
        "validation_raw": base.get("heldout_raw"),
        "validation_reliability_metrics": metrics,
        "minimum_fitted_block_count": block_min_count,
        "certification_review_eligible": eligible,
        "reasons": reasons,
    }
    review_sha = _canonical_hash(review_body)
    return {
        "mode": "CALIBRATION_CERTIFICATION_REVIEW",
        **review_body,
        "review_sha256": review_sha,
        "calibration_verified": False,
        "calibration_certificate_issued": False,
        "model_promotion_applied": False,
        "requires_human_acceptance": True,
        "status": (
            "CALIBRATION_CERTIFICATION_REVIEW_ELIGIBLE"
            if eligible else "HOLD"
        ),
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "note": (
            "Passing this review means the temporal calibration package satisfies "
            "the predeclared research acceptance policy. It does not itself certify "
            "calibration or authorize a live model."
        ),
    }


def verify_calibration_review_receipt(receipt: Mapping[str, Any]) -> bool:
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("mode") != "CALIBRATION_CERTIFICATION_REVIEW"
    ):
        raise ValueError("calibration certification review receipt required")
    supplied = _sha(receipt.get("review_sha256"), "review_sha256")
    body_keys = {
        "scope", "fit_at", "assessed_at", "research_policy",
        "acceptance_policy", "underlying_assessment_status", "counts",
        "training_sha256", "validation_sha256", "calibration_map_sha256",
        "calibration_blocks", "validation_calibrated", "validation_raw",
        "validation_reliability_metrics", "minimum_fitted_block_count",
        "certification_review_eligible", "reasons",
    }
    body = {key: receipt.get(key) for key in body_keys}
    if _canonical_hash(body) != supplied:
        raise ValueError("calibration review receipt hash mismatch")
    if receipt.get("calibration_verified") is not False:
        raise ValueError("review receipt cannot self-certify calibration")
    if receipt.get("calibration_certificate_issued") is not False:
        raise ValueError("review receipt cannot issue a certificate")
    if receipt.get("model_promotion_applied") is not False:
        raise ValueError("review receipt cannot promote a model")
    return True


def candidate_calibration_uncertainty_diagnostic(
    review_receipt: Mapping[str, Any],
    raw_probability: Any,
    *,
    trials: int,
    seed: int,
):
    """Map raw p to an isotonic block and quantify local Jeffreys uncertainty."""
    verify_calibration_review_receipt(review_receipt)
    if review_receipt.get("certification_review_eligible") is not True:
        raise ValueError("eligible calibration review receipt required")
    if type(trials) is not int or trials < 100000:
        raise ValueError("at least 100000 Jeffreys posterior trials required")
    if type(seed) is not int:
        raise ValueError("integer deterministic seed required")
    p = Fraction(exact_probability(raw_probability))
    blocks = review_receipt.get("calibration_blocks")
    upper, values = compile_blocks(blocks)
    index = min(bisect_left(upper, p), len(values) - 1)
    block = blocks[index]
    count = block["count"]
    wins = block["wins"]
    if type(count) is not int or count <= 0 or type(wins) is not int:
        raise ValueError("invalid calibration block counts")
    losses = count - wins
    if losses < 0:
        raise ValueError("calibration wins exceed count")

    rng = random.Random(seed)
    samples = [
        rng.betavariate(wins + 0.5, losses + 0.5)
        for _ in range(trials)
    ]
    samples.sort()

    def quantile(fraction):
        idx = int(round((len(samples) - 1) * fraction))
        return samples[idx]

    calibrated = float(values[index])
    lower = quantile(0.05)
    median = quantile(0.50)
    upper95 = quantile(0.95)
    return {
        "mode": "CANDIDATE_CALIBRATION_UNCERTAINTY_DIAGNOSTIC",
        "raw_probability": float(p),
        "calibration_block_index": index,
        "calibration_block_count": count,
        "calibration_block_wins": wins,
        "isotonic_calibrated_probability": calibrated,
        "jeffreys_probability_p05": lower,
        "jeffreys_probability_p50": median,
        "jeffreys_probability_p95": upper95,
        "trials": trials,
        "seed": seed,
        "black_diamond_probability_thresholds_modeled": {
            "calibrated_probability_at_least_87": calibrated >= 0.87,
            "lower_bound_at_least_80": lower >= 0.80,
            "both_modeled_probability_gates": calibrated >= 0.87 and lower >= 0.80,
        },
        "calibration_verified": False,
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "note": (
            "Jeffreys bounds quantify uncertainty in this fitted calibration block. "
            "They are not a live Black Diamond certification without an independently "
            "accepted calibration certificate and all remaining V7 gates."
        ),
    }
