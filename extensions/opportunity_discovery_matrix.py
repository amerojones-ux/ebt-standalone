"""EBT.ai V7/V7.1 opportunity-discovery matrix (offline research only).

This module separates safe alternate-line discovery, role-change rerun triggers,
rare-event asymmetric value, and screenshot/result quarantine. It never fits a
projection from sportsbook prices, never claims calibration, and never approves
a wager.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable

from .underperformance import num, quantile, validated_pmf

COMPARATORS = {"GE", "GT", "LT", "LE"}
ACTIVE = {"ACTIVE", "AVAILABLE", "PROBABLE"}
INACTIVE = {"OUT", "INACTIVE", "SUSPENDED"}


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


def american_decimal_odds(odds: Any) -> Decimal:
    if isinstance(odds, bool) or type(odds) is not int or odds == 0 or -100 < odds < 100:
        raise ValueError("American odds must be integer <= -100 or >= +100")
    if odds > 0:
        return Decimal(1) + Decimal(odds) / Decimal(100)
    return Decimal(1) + Decimal(100) / Decimal(abs(odds))


def raw_implied_probability(odds: Any) -> Decimal:
    return Decimal(1) / american_decimal_odds(odds)


def _settlement(pmf, comparator, threshold):
    if comparator not in COMPARATORS:
        raise ValueError("unsupported comparator")
    if comparator == "GE":
        win = sum((p for y, p in pmf.items() if Decimal(y) >= threshold), Decimal(0))
        push = Decimal(0)
    elif comparator == "GT":
        win = sum((p for y, p in pmf.items() if Decimal(y) > threshold), Decimal(0))
        push = sum((p for y, p in pmf.items() if Decimal(y) == threshold), Decimal(0))
    elif comparator == "LT":
        win = sum((p for y, p in pmf.items() if Decimal(y) < threshold), Decimal(0))
        push = sum((p for y, p in pmf.items() if Decimal(y) == threshold), Decimal(0))
    else:
        win = sum((p for y, p in pmf.items() if Decimal(y) <= threshold), Decimal(0))
        push = Decimal(0)
    lose = Decimal(1) - win - push
    return win, push, lose


def _cushion(p50, threshold, comparator):
    return Decimal(p50) - threshold if comparator in {"GE", "GT"} else threshold - Decimal(p50)


def _discovery_policy(policy):
    required = {
        "safe_modeled_probability_min",
        "tail_modeled_probability_min",
        "minimum_probability_edge",
    }
    if not isinstance(policy, dict) or set(policy) != required:
        raise ValueError("exact predeclared market-family discovery policy required")
    out = {k: num(v) for k, v in policy.items()}
    if not (Decimal(0) < out["tail_modeled_probability_min"]
            <= out["safe_modeled_probability_min"] <= Decimal(1)):
        raise ValueError("invalid modeled-probability policy ordering")
    if not (Decimal(0) <= out["minimum_probability_edge"] < Decimal(1)):
        raise ValueError("minimum_probability_edge must be in [0,1)")
    return out


def discover_count_market_expressions(
    predictive_pmf: Dict[str, Any],
    quotes: Iterable[Dict[str, Any]],
    *,
    projection_locked_at: str,
    market_family_policy: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare a locked independent count PMF with a complete operator ladder."""
    pmf = validated_pmf(predictive_pmf)
    lock = _clock(projection_locked_at, "projection_locked_at")
    policy = _discovery_policy(market_family_policy)
    p50 = quantile(pmf, ".5")
    seen = set()
    rows = []

    for q in list(quotes):
        required = {
            "market_id", "book", "comparator", "threshold", "american_odds",
            "quoted_at", "ingested_at", "price_verified",
        }
        if not isinstance(q, dict) or set(q) != required:
            raise ValueError("exact market quote schema required")
        if not isinstance(q["market_id"], str) or not q["market_id"].strip() or q["market_id"] in seen:
            raise ValueError("unique nonblank market_id required")
        seen.add(q["market_id"])
        comparator = q["comparator"]
        threshold = num(q["threshold"])
        if comparator not in COMPARATORS or threshold < 0:
            raise ValueError("invalid comparator or threshold")
        quoted = _clock(q["quoted_at"], "quoted_at")
        ingested = _clock(q["ingested_at"], "ingested_at")
        if quoted > ingested:
            raise ValueError("quote cannot be ingested before effective time")
        if ingested < lock:
            raise ValueError("market ingested before independent projection lock")
        if type(q["price_verified"]) is not bool:
            raise ValueError("price_verified boolean required")

        win, push, lose = _settlement(pmf, comparator, threshold)
        implied = raw_implied_probability(q["american_odds"])
        edge = win - implied
        d = american_decimal_odds(q["american_odds"])
        ev_diag = win * (d - Decimal(1)) - lose
        cushion = _cushion(p50, threshold, comparator)

        if win >= policy["safe_modeled_probability_min"] and cushion > 0:
            lane = "SAFE_ALT_RESEARCH"
        elif (win >= policy["tail_modeled_probability_min"]
              and edge >= policy["minimum_probability_edge"] and ev_diag > 0):
            lane = "TAIL_VALUE_RESEARCH"
        else:
            lane = "SHADOW"

        rows.append({
            "market_id": q["market_id"],
            "book": q["book"],
            "comparator": comparator,
            "threshold": str(threshold),
            "american_odds": q["american_odds"],
            "price_verified": q["price_verified"],
            "modeled_win_probability": float(win),
            "modeled_push_probability": float(push),
            "modeled_lose_probability": float(lose),
            "raw_implied_probability": float(implied),
            "modeled_probability_minus_raw_implied": float(edge),
            "uncalibrated_ev_diagnostic": float(ev_diag),
            "p50": p50,
            "central_cushion_units": str(cushion),
            "lane": lane,
            "wager_status": "NOT APPROVED",
        })
    if not rows:
        raise ValueError("at least one quote required")

    ordered = sorted(rows, key=lambda x: x["modeled_win_probability"])
    knee = None
    best_ratio = None
    for prev, cur in zip(ordered, ordered[1:]):
        dp = Decimal(str(cur["modeled_win_probability"])) - Decimal(str(prev["modeled_win_probability"]))
        dc = Decimal(str(cur["raw_implied_probability"])) - Decimal(str(prev["raw_implied_probability"]))
        if dp <= 0:
            continue
        ratio = None if dc <= 0 else dp / dc
        if dc <= 0 or best_ratio is None or (ratio is not None and ratio > best_ratio):
            best_ratio = ratio
            knee = {
                "market_id": cur["market_id"],
                "versus_market_id": prev["market_id"],
                "survival_gain": float(dp),
                "raw_implied_cost": float(dc),
                "gain_per_implied_cost": None if ratio is None else float(ratio),
                "price_order_anomaly": dc <= 0,
            }

    return {
        "mode": "OFFLINE_MARKET_EXPRESSION_DISCOVERY",
        "forecast_status": "HOLD",
        "wager_status": "NOT APPROVED",
        "calibration_verified": False,
        "no_vig_probability_calculated": False,
        "projection_locked_before_market_ingestion": True,
        "p50": p50,
        "policy": {k: str(v) for k, v in policy.items()},
        "expressions": sorted(rows, key=lambda x: x["modeled_win_probability"], reverse=True),
        "efficiency_knee_diagnostic": knee,
    }


def detect_role_reallocation(
    before: Dict[str, Any],
    after: Dict[str, Any],
    *,
    event_start: str,
    unit: str,
    official_confirmation: bool,
    source_status: str,
    material_share_threshold: Any,
) -> Dict[str, Any]:
    """Detect pregame role/opportunity changes and force a fresh independent rerun."""
    start = _clock(event_start, "event_start")
    threshold = num(material_share_threshold)
    if not Decimal(0) < threshold <= Decimal(1):
        raise ValueError("material_share_threshold must be in (0,1]")
    if type(official_confirmation) is not bool:
        raise ValueError("official_confirmation boolean required")
    if source_status not in {"FOUND", "CONFLICTING", "STALE", "BLOCKED", "N/A"}:
        raise ValueError("invalid V7 source status")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("opportunity unit required")

    def snap(raw, label):
        if not isinstance(raw, dict) or not raw:
            raise ValueError(f"{label} snapshot required")
        out = {}
        for pid, row in raw.items():
            required = {"availability", "role", "expected_opportunity", "available_at"}
            if not isinstance(pid, str) or not pid.strip() or not isinstance(row, dict) or set(row) != required:
                raise ValueError("exact canonical role row required")
            available_at = _clock(row["available_at"], f"{label}.{pid}.available_at")
            if available_at >= start:
                raise ValueError("post-start role evidence cannot drive pregame reallocation")
            opp = num(row["expected_opportunity"])
            if opp < 0:
                raise ValueError("expected_opportunity must be nonnegative")
            out[pid] = {
                "availability": str(row["availability"]).upper(),
                "role": str(row["role"]).upper(),
                "expected_opportunity": opp,
            }
        return out

    old, new = snap(before, "before"), snap(after, "after")
    players = sorted(set(old) | set(new))
    before_total = sum((old.get(p, {}).get("expected_opportunity", Decimal(0)) for p in players), Decimal(0))
    after_total = sum((new.get(p, {}).get("expected_opportunity", Decimal(0)) for p in players), Decimal(0))
    scale = max(before_total, after_total, Decimal(1))
    changes = []

    for pid in players:
        a = old.get(pid, {"availability": "UNLISTED", "role": "UNLISTED", "expected_opportunity": Decimal(0)})
        b = new.get(pid, {"availability": "UNLISTED", "role": "UNLISTED", "expected_opportunity": Decimal(0)})
        delta = b["expected_opportunity"] - a["expected_opportunity"]
        material = abs(delta) / scale >= threshold
        if a["availability"] != b["availability"] or a["role"] != b["role"] or material:
            changes.append({
                "player_id": pid,
                "availability_before": a["availability"],
                "availability_after": b["availability"],
                "role_before": a["role"],
                "role_after": b["role"],
                "opportunity_before": str(a["expected_opportunity"]),
                "opportunity_after": str(b["expected_opportunity"]),
                "opportunity_delta": str(delta),
                "beneficiary": delta > 0,
                "material": material,
            })

    forced_absence = any(
        c["availability_before"] in ACTIVE and c["availability_after"] in INACTIVE for c in changes
    )
    role_change = any(c["role_before"] != c["role_after"] for c in changes)
    material_change = forced_absence or role_change or any(c["material"] for c in changes)
    if material_change and official_confirmation and source_status == "FOUND":
        action = "FULL_RERUN_REQUIRED"
    elif material_change:
        action = "HOLD_FOR_CONFIRMATION"
    else:
        action = "NO_MATERIAL_CHANGE"

    beneficiaries = sorted(
        [c for c in changes if c["beneficiary"]],
        key=lambda x: Decimal(x["opportunity_delta"]),
        reverse=True,
    )
    return {
        "mode": "PREGAME_ROLE_REALLOCATION_TRIGGER",
        "unit": unit,
        "material_change": material_change,
        "forced_absence_detected": forced_absence,
        "starter_or_role_change_detected": role_change,
        "decision_action": action,
        "beneficiaries": beneficiaries,
        "all_changes": changes,
        "markets_to_revalidate": "ALL_ROLE_SENSITIVE_MARKETS" if material_change else [],
        "forecast_status": "HOLD" if action != "NO_MATERIAL_CHANGE" else "UNCHANGED",
        "wager_status": "NOT APPROVED",
    }


def competing_risk_probabilities(hazard_scores: Dict[str, Any], *, no_event_hazard: Any = 0):
    """Normalize independently modeled rare-event hazard scores."""
    if not isinstance(hazard_scores, dict) or len(hazard_scores) < 2:
        raise ValueError("at least two candidate hazards required")
    hazards = {}
    for cid, raw in hazard_scores.items():
        h = num(raw)
        if not isinstance(cid, str) or not cid.strip() or h < 0:
            raise ValueError("invalid candidate hazard")
        hazards[cid] = h
    no_event = num(no_event_hazard)
    total = sum(hazards.values(), Decimal(0)) + no_event
    if no_event < 0 or total <= 0:
        raise ValueError("invalid total hazard")
    return {
        "candidate_probabilities": {k: float(v / total) for k, v in hazards.items()},
        "no_event_probability": float(no_event / total),
        "assumption": "constant proportional competing hazards",
        "calibration_verified": False,
    }


def evaluate_rare_event_quotes(
    fair_probabilities: Dict[str, Any],
    quotes: Iterable[Dict[str, Any]],
    *,
    model_locked_at: str,
    minimum_probability_edge: Any,
    minimum_modeled_probability: Any,
) -> Dict[str, Any]:
    """Route rare events to asymmetric-value research without calling them safe."""
    lock = _clock(model_locked_at, "model_locked_at")
    min_edge, min_prob = num(minimum_probability_edge), num(minimum_modeled_probability)
    probs = {cid: num(p) for cid, p in fair_probabilities.items()}
    if not Decimal(0) <= min_edge < Decimal(1) or not Decimal(0) < min_prob <= Decimal(1):
        raise ValueError("invalid rare-event policy")
    if any(p < 0 or p > 1 for p in probs.values()) or sum(probs.values(), Decimal(0)) > Decimal(1) + Decimal("1e-10"):
        raise ValueError("invalid rare-event probabilities")
    rows, seen = [], set()
    for q in list(quotes):
        required = {"candidate_id", "book", "american_odds", "quoted_at", "ingested_at", "price_verified"}
        if not isinstance(q, dict) or set(q) != required:
            raise ValueError("exact rare-event quote schema required")
        cid = q["candidate_id"]
        if cid not in probs or cid in seen:
            raise ValueError("unknown or duplicate rare-event candidate")
        seen.add(cid)
        quoted, ingested = _clock(q["quoted_at"], "quoted_at"), _clock(q["ingested_at"], "ingested_at")
        if quoted > ingested or ingested < lock:
            raise ValueError("rare-event price chronology violates projection-before-market")
        implied = raw_implied_probability(q["american_odds"])
        p = probs[cid]
        d = american_decimal_odds(q["american_odds"])
        edge = p - implied
        ev_diag = p * (d - Decimal(1)) - (Decimal(1) - p)
        lane = "ASYMMETRIC_VALUE_RESEARCH" if p >= min_prob and edge >= min_edge and ev_diag > 0 else "SHADOW"
        rows.append({
            "candidate_id": cid,
            "book": q["book"],
            "american_odds": q["american_odds"],
            "price_verified": q["price_verified"],
            "modeled_probability": float(p),
            "raw_implied_probability": float(implied),
            "modeled_probability_minus_raw_implied": float(edge),
            "uncalibrated_ev_diagnostic": float(ev_diag),
            "lane": lane,
            "black_diamond_survival_eligible": False,
            "forecast_status": "HOLD",
            "wager_status": "NOT APPROVED",
        })
    if not rows:
        raise ValueError("at least one rare-event quote required")
    return {
        "mode": "RARE_EVENT_ASYMMETRIC_VALUE_RESEARCH",
        "calibration_verified": False,
        "black_diamond_survival_lane": False,
        "candidates": sorted(rows, key=lambda x: x["modeled_probability_minus_raw_implied"], reverse=True),
    }


def reconcile_result_claim(claim: Dict[str, Any], official: Dict[str, Any]) -> Dict[str, Any]:
    """Quarantine screenshot/ticket result claims that conflict with official settlement."""
    required = {"event_id", "participant_a_id", "participant_b_id", "score_a", "score_b", "player_stats"}
    if not isinstance(claim, dict) or not isinstance(official, dict) or set(claim) != required or set(official) != required:
        raise ValueError("exact result reconciliation schema required")
    conflicts = []
    for field in ("event_id", "participant_a_id", "participant_b_id", "score_a", "score_b"):
        if claim[field] != official[field]:
            conflicts.append({"field": field, "claim": claim[field], "official": official[field]})
    if not isinstance(claim["player_stats"], dict) or not isinstance(official["player_stats"], dict):
        raise ValueError("player_stats objects required")
    for key, value in claim["player_stats"].items():
        if key not in official["player_stats"] or official["player_stats"][key] != value:
            conflicts.append({
                "field": f"player_stats.{key}",
                "claim": value,
                "official": official["player_stats"].get(key, "MISSING"),
            })
    status = "QUARANTINED" if conflicts else "RECONCILED"
    return {
        "mode": "POSTGAME_RESULT_CLAIM_FIREWALL",
        "status": status,
        "eligible_for_model_learning": status == "RECONCILED",
        "conflicts": conflicts,
        "rule": "Screenshot/ticket evidence cannot override verified official settlement.",
    }
