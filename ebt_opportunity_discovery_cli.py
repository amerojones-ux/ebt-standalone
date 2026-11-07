"""Offline CLI for the V7/V7.1 Opportunity Discovery Matrix."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.opportunity_discovery_matrix import (
    competing_risk_probabilities,
    detect_role_reallocation,
    discover_count_market_expressions,
    evaluate_rare_event_quotes,
    reconcile_result_claim,
)


def _obj(path):
    row = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError("input JSON object required")
    return row


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline fail-closed opportunity discovery research")
    sub = p.add_subparsers(dest="mode", required=True)
    for name in ("market-discovery", "role-reallocation", "rare-event", "result-integrity"):
        a = sub.add_parser(name)
        a.add_argument("input")
    args = p.parse_args(argv)

    try:
        row = _obj(args.input)
        if args.mode == "market-discovery":
            if set(row) != {"predictive_pmf","quotes","projection_locked_at","market_family_policy"}:
                raise ValueError("exact market-discovery schema required")
            result = discover_count_market_expressions(
                row["predictive_pmf"], row["quotes"],
                projection_locked_at=row["projection_locked_at"],
                market_family_policy=row["market_family_policy"])
        elif args.mode == "role-reallocation":
            required = {
                "before","after","event_start","unit","official_confirmation",
                "source_status","material_share_threshold",
            }
            if set(row) != required:
                raise ValueError("exact role-reallocation schema required")
            result = detect_role_reallocation(
                row["before"], row["after"], event_start=row["event_start"],
                unit=row["unit"], official_confirmation=row["official_confirmation"],
                source_status=row["source_status"],
                material_share_threshold=row["material_share_threshold"])
        elif args.mode == "rare-event":
            required = {
                "hazard_scores","no_event_hazard","quotes","model_locked_at",
                "minimum_probability_edge","minimum_modeled_probability",
            }
            if set(row) != required:
                raise ValueError("exact rare-event schema required")
            fair = competing_risk_probabilities(
                row["hazard_scores"], no_event_hazard=row["no_event_hazard"])
            priced = evaluate_rare_event_quotes(
                fair["candidate_probabilities"], row["quotes"],
                model_locked_at=row["model_locked_at"],
                minimum_probability_edge=row["minimum_probability_edge"],
                minimum_modeled_probability=row["minimum_modeled_probability"])
            result = {"model": fair, "price_comparison": priced}
        else:
            if set(row) != {"claim","official"}:
                raise ValueError("exact result-integrity schema required")
            result = reconcile_result_claim(row["claim"], row["official"])
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, ArithmeticError, OverflowError) as exc:
        print(json.dumps({"status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
