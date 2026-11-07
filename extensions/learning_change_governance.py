"""V7/V7.1 model-learning change governance.

This module enforces the minimum evidence required before a proposed model-weight
or threshold change may ENTER human review. It never mutates weights, promotes a
model, or approves a forecast/wager.

Authoritative V7 safeguards enforced here:
- >=30 settled observations per market
- >=50 settled observations per model
- >=2 non-overlapping degraded windows
- each degraded window: Brier worsening >=0.02 OR calibration gap >=0.05
- completed root-cause review
- completed held-out backtest
- new model version
- explicit rollback version/path
- isolated hits/misses/screenshots/tickets cannot authorize change
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Dict, Mapping, Sequence

from .underperformance import num

BARRIER_BRIER_WORSENING = Decimal("0.02")
BARRIER_CALIBRATION_GAP = Decimal("0.05")
MIN_SETTLED_PER_MARKET = 30
MIN_SETTLED_PER_MODEL = 50

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIABILITY = {
    "PRE_GAME_IDENTIFIABLE",
    "PARTIALLY_IDENTIFIABLE",
    "POSTGAME_ONLY",
}
NONAUTHORITATIVE_ISOLATED_KINDS = {"SCREENSHOT", "TICKET", "ISOLATED_OUTCOME"}


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


def _prob_metric(value: Any, field: str) -> Decimal:
    metric = num(value)
    if not Decimal(0) <= metric <= Decimal(1):
        raise ValueError(f"{field} must be in [0,1]")
    return metric


def _window(raw: Mapping[str, Any]) -> Dict[str, Any]:
    required = {
        "window_id", "start", "end", "settled_count",
        "brier_reference", "brier_current", "calibration_gap_current",
        "evidence_sha256",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("exact degraded-window schema required")
    window_id = raw["window_id"]
    if not isinstance(window_id, str) or not window_id.strip():
        raise ValueError("window_id required")
    start = _clock(raw["start"], f"{window_id}.start")
    end = _clock(raw["end"], f"{window_id}.end")
    if not start < end:
        raise ValueError("degraded window end must follow start")
    count = raw["settled_count"]
    if type(count) is not int or count <= 0:
        raise ValueError("degraded-window settled_count must be positive integer")
    brier_reference = _prob_metric(raw["brier_reference"], "brier_reference")
    brier_current = _prob_metric(raw["brier_current"], "brier_current")
    gap = _prob_metric(raw["calibration_gap_current"], "calibration_gap_current")
    evidence_sha = _sha(raw["evidence_sha256"], f"{window_id}.evidence_sha256")
    brier_worsening = brier_current - brier_reference
    qualifies = (
        brier_worsening >= BARRIER_BRIER_WORSENING
        or gap >= BARRIER_CALIBRATION_GAP
    )
    return {
        "window_id": window_id.strip(),
        "start": start,
        "end": end,
        "settled_count": count,
        "brier_reference": brier_reference,
        "brier_current": brier_current,
        "brier_worsening": brier_worsening,
        "calibration_gap_current": gap,
        "qualifies_as_degraded": qualifies,
        "evidence_sha256": evidence_sha,
    }


def _validate_windows(rows: Sequence[Mapping[str, Any]], review_cutoff: datetime):
    if not isinstance(rows, (list, tuple)) or len(rows) < 2:
        raise ValueError("at least two degraded windows required")
    windows = [_window(row) for row in rows]
    ids = [row["window_id"] for row in windows]
    if len(ids) != len(set(ids)):
        raise ValueError("unique degraded-window IDs required")
    windows.sort(key=lambda row: (row["start"], row["window_id"]))
    for row in windows:
        if row["end"] >= review_cutoff:
            raise ValueError("degraded window must end before review cutoff")
    for left, right in zip(windows, windows[1:]):
        if left["end"] > right["start"]:
            raise ValueError("degraded windows must not overlap")
    return windows


def _evidence_items(items):
    if not isinstance(items, list) or not items:
        raise ValueError("root-cause evidence_items required")
    normalized = []
    for item in items:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"kind", "sha256"}
            or not isinstance(item["kind"], str)
            or not item["kind"].strip()
        ):
            raise ValueError("exact root-cause evidence item required")
        normalized.append({
            "kind": item["kind"].strip().upper(),
            "sha256": _sha(item["sha256"], "root_cause.evidence.sha256"),
        })
    return normalized


def _root_cause(raw: Mapping[str, Any], review_cutoff: datetime):
    required = {
        "completed", "completed_at", "finding", "identifiability",
        "isolated_outcome_only", "evidence_items",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("exact root-cause review schema required")
    if type(raw["completed"]) is not bool:
        raise ValueError("root_cause.completed boolean required")
    completed_at = _clock(raw["completed_at"], "root_cause.completed_at")
    if completed_at > review_cutoff:
        raise ValueError("root-cause review cannot be completed after review cutoff")
    finding = raw["finding"]
    if not isinstance(finding, str) or not finding.strip():
        raise ValueError("root-cause finding required")
    identifiability = raw["identifiability"]
    if identifiability not in IDENTIFIABILITY:
        raise ValueError("invalid root-cause identifiability")
    if type(raw["isolated_outcome_only"]) is not bool:
        raise ValueError("isolated_outcome_only boolean required")
    evidence = _evidence_items(raw["evidence_items"])
    kinds = {item["kind"] for item in evidence}
    has_nonisolated_evidence = bool(kinds - NONAUTHORITATIVE_ISOLATED_KINDS)
    return {
        "completed": raw["completed"],
        "completed_at": completed_at,
        "finding": finding.strip(),
        "identifiability": identifiability,
        "isolated_outcome_only": raw["isolated_outcome_only"],
        "evidence_items": evidence,
        "has_nonisolated_evidence": has_nonisolated_evidence,
    }


def _backtest(raw: Mapping[str, Any], review_cutoff: datetime):
    required = {
        "completed", "completed_at", "baseline_version", "candidate_version",
        "heldout_events", "heldout_brier_baseline", "heldout_brier_candidate",
        "heldout_calibration_gap_baseline", "heldout_calibration_gap_candidate",
        "evidence_sha256",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("exact held-out backtest schema required")
    if type(raw["completed"]) is not bool:
        raise ValueError("backtest.completed boolean required")
    completed_at = _clock(raw["completed_at"], "backtest.completed_at")
    if completed_at > review_cutoff:
        raise ValueError("backtest cannot be completed after review cutoff")
    for field in ("baseline_version", "candidate_version"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise ValueError(f"{field} required")
    heldout = raw["heldout_events"]
    if type(heldout) is not int or heldout <= 0:
        raise ValueError("positive heldout_events required")
    brier_base = _prob_metric(raw["heldout_brier_baseline"], "heldout_brier_baseline")
    brier_candidate = _prob_metric(raw["heldout_brier_candidate"], "heldout_brier_candidate")
    gap_base = _prob_metric(
        raw["heldout_calibration_gap_baseline"],
        "heldout_calibration_gap_baseline",
    )
    gap_candidate = _prob_metric(
        raw["heldout_calibration_gap_candidate"],
        "heldout_calibration_gap_candidate",
    )
    evidence_sha = _sha(raw["evidence_sha256"], "backtest.evidence_sha256")
    return {
        "completed": raw["completed"],
        "completed_at": completed_at,
        "baseline_version": raw["baseline_version"].strip(),
        "candidate_version": raw["candidate_version"].strip(),
        "heldout_events": heldout,
        "heldout_brier_baseline": brier_base,
        "heldout_brier_candidate": brier_candidate,
        "heldout_calibration_gap_baseline": gap_base,
        "heldout_calibration_gap_candidate": gap_candidate,
        "brier_delta_candidate_minus_baseline": brier_candidate - brier_base,
        "calibration_gap_delta_candidate_minus_baseline": gap_candidate - gap_base,
        "evidence_sha256": evidence_sha,
    }


def _versioning(raw: Mapping[str, Any]):
    required = {
        "current_version", "proposed_version", "rollback_version", "rollback_path",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise ValueError("exact versioning schema required")
    for field in ("current_version", "proposed_version", "rollback_version", "rollback_path"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise ValueError(f"{field} required")
    return {key: raw[key].strip() for key in required}


def assess_learning_change_review(
    request: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return review eligibility only; never apply or promote a change."""
    required = {
        "request_id", "market_key", "settled_market_count", "settled_model_count",
        "settled_market_sample_sha256", "settled_model_sample_sha256",
        "review_cutoff", "degraded_windows", "root_cause", "backtest",
        "versioning", "proposed_change_summary",
    }
    if not isinstance(request, Mapping) or set(request) != required:
        raise ValueError("exact learning-change request schema required")
    for field in ("request_id", "market_key", "proposed_change_summary"):
        if not isinstance(request[field], str) or not request[field].strip():
            raise ValueError(f"{field} required")
    market_count = request["settled_market_count"]
    model_count = request["settled_model_count"]
    if type(market_count) is not int or market_count < 0:
        raise ValueError("settled_market_count must be nonnegative integer")
    if type(model_count) is not int or model_count < 0:
        raise ValueError("settled_model_count must be nonnegative integer")
    market_sample_sha = _sha(
        request["settled_market_sample_sha256"],
        "settled_market_sample_sha256",
    )
    model_sample_sha = _sha(
        request["settled_model_sample_sha256"],
        "settled_model_sample_sha256",
    )
    cutoff = _clock(request["review_cutoff"], "review_cutoff")
    windows = _validate_windows(request["degraded_windows"], cutoff)
    root = _root_cause(request["root_cause"], cutoff)
    backtest = _backtest(request["backtest"], cutoff)
    versioning = _versioning(request["versioning"])

    reasons = []
    if market_count < MIN_SETTLED_PER_MARKET:
        reasons.append("INSUFFICIENT_SETTLED_MARKET_SAMPLE")
    if model_count < MIN_SETTLED_PER_MODEL:
        reasons.append("INSUFFICIENT_SETTLED_MODEL_SAMPLE")

    qualifying = [row for row in windows if row["qualifies_as_degraded"]]
    if len(qualifying) < 2:
        reasons.append("FEWER_THAN_TWO_QUALIFYING_DEGRADED_WINDOWS")
    for row in windows:
        if not row["qualifies_as_degraded"]:
            reasons.append(f"WINDOW_NOT_DEGRADED:{row['window_id']}")

    if root["completed"] is not True:
        reasons.append("ROOT_CAUSE_REVIEW_INCOMPLETE")
    if root["isolated_outcome_only"] is True:
        reasons.append("ROOT_CAUSE_ISOLATED_OUTCOME_ONLY")
    if not root["has_nonisolated_evidence"]:
        reasons.append("ROOT_CAUSE_LACKS_NONISOLATED_EVIDENCE")
    if root["identifiability"] == "POSTGAME_ONLY":
        reasons.append("ROOT_CAUSE_POSTGAME_ONLY_NOT_PRODUCTION_LEARNING_EVIDENCE")

    if backtest["completed"] is not True:
        reasons.append("HELDOUT_BACKTEST_INCOMPLETE")

    if versioning["proposed_version"] == versioning["current_version"]:
        reasons.append("PROPOSED_VERSION_NOT_NEW")
    if versioning["rollback_version"] != versioning["current_version"]:
        reasons.append("ROLLBACK_VERSION_MUST_MATCH_CURRENT_VERSION")

    if backtest["baseline_version"] != versioning["current_version"]:
        reasons.append("BACKTEST_BASELINE_VERSION_MISMATCH")
    if backtest["candidate_version"] != versioning["proposed_version"]:
        reasons.append("BACKTEST_CANDIDATE_VERSION_MISMATCH")

    eligible = not reasons
    window_rows = [
        {
            "window_id": row["window_id"],
            "start": row["start"].isoformat(),
            "end": row["end"].isoformat(),
            "settled_count": row["settled_count"],
            "brier_reference": str(row["brier_reference"]),
            "brier_current": str(row["brier_current"]),
            "brier_worsening": str(row["brier_worsening"]),
            "calibration_gap_current": str(row["calibration_gap_current"]),
            "qualifies_as_degraded": row["qualifies_as_degraded"],
            "evidence_sha256": row["evidence_sha256"],
        }
        for row in windows
    ]
    root_out = {
        **root,
        "completed_at": root["completed_at"].isoformat(),
    }
    backtest_out = {
        **backtest,
        "completed_at": backtest["completed_at"].isoformat(),
        "heldout_brier_baseline": str(backtest["heldout_brier_baseline"]),
        "heldout_brier_candidate": str(backtest["heldout_brier_candidate"]),
        "heldout_calibration_gap_baseline": str(
            backtest["heldout_calibration_gap_baseline"]
        ),
        "heldout_calibration_gap_candidate": str(
            backtest["heldout_calibration_gap_candidate"]
        ),
        "brier_delta_candidate_minus_baseline": str(
            backtest["brier_delta_candidate_minus_baseline"]
        ),
        "calibration_gap_delta_candidate_minus_baseline": str(
            backtest["calibration_gap_delta_candidate_minus_baseline"]
        ),
    }
    review_body = {
        "request_id": request["request_id"].strip(),
        "market_key": request["market_key"].strip(),
        "settled_market_count": market_count,
        "settled_model_count": model_count,
        "settled_market_sample_sha256": market_sample_sha,
        "settled_model_sample_sha256": model_sample_sha,
        "review_cutoff": cutoff.isoformat(),
        "degraded_windows": window_rows,
        "root_cause": root_out,
        "backtest": backtest_out,
        "versioning": versioning,
        "proposed_change_summary": request["proposed_change_summary"].strip(),
        "eligible_for_model_change_review": eligible,
        "reasons": reasons,
    }
    review_sha = hashlib.sha256(
        json.dumps(
            review_body,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return {
        "mode": "V7_LEARNING_CHANGE_REVIEW_GATE",
        **review_body,
        "v7_thresholds": {
            "minimum_settled_per_market": MIN_SETTLED_PER_MARKET,
            "minimum_settled_per_model": MIN_SETTLED_PER_MODEL,
            "minimum_degraded_windows": 2,
            "brier_worsening_trigger": str(BARRIER_BRIER_WORSENING),
            "calibration_gap_trigger": str(BARRIER_CALIBRATION_GAP),
        },
        "review_sha256": review_sha,
        "weight_change_applied": False,
        "threshold_change_applied": False,
        "model_promotion_applied": False,
        "requires_human_acceptance": True,
        "status": (
            "LEARNING_CHANGE_REVIEW_ELIGIBLE"
            if eligible
            else "HOLD"
        ),
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "note": (
            "Eligibility permits human review only. It does not prove the candidate "
            "model is better, change production weights, or alter any live forecast."
        ),
    }


def verify_learning_review_receipt(receipt: Mapping[str, Any]) -> bool:
    """Verify immutable review SHA without authorizing promotion."""
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("mode") != "V7_LEARNING_CHANGE_REVIEW_GATE"
    ):
        raise ValueError("learning review receipt required")
    supplied = _sha(receipt.get("review_sha256"), "review_sha256")
    body_keys = {
        "request_id", "market_key", "settled_market_count", "settled_model_count",
        "settled_market_sample_sha256", "settled_model_sample_sha256",
        "review_cutoff", "degraded_windows", "root_cause", "backtest",
        "versioning", "proposed_change_summary",
        "eligible_for_model_change_review", "reasons",
    }
    body = {key: receipt.get(key) for key in body_keys}
    expected = hashlib.sha256(
        json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    if expected != supplied:
        raise ValueError("learning review receipt hash mismatch")
    if receipt.get("weight_change_applied") is not False:
        raise ValueError("learning review receipt cannot apply weight changes")
    if receipt.get("threshold_change_applied") is not False:
        raise ValueError("learning review receipt cannot apply threshold changes")
    if receipt.get("model_promotion_applied") is not False:
        raise ValueError("learning review receipt cannot promote a model")
    return True
