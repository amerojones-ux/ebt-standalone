"""Offline CLI for Bayesian rare-event research distributions."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.bayesian_rare_events import (
    fit_binary_rare_event_posterior,
    fit_competing_event_posterior,
    run_three_competing_event_scenarios,
    simulate_binary_posterior_uncertainty,
    simulate_competing_posterior_uncertainty,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline Bayesian rare-event research")
    sub=p.add_subparsers(dest="mode",required=True)
    for name in ("fit-competing","simulate-competing","three-competing","fit-binary","simulate-binary"):
        a=sub.add_parser(name)
        a.add_argument("input")
    args=p.parse_args(argv)
    try:
        row=load(args.input)
        if not isinstance(row,dict):
            raise ValueError("input object required")
        if args.mode=="fit-competing":
            if set(row)!={"rows","cutoff","residual_category_id","candidate_universe_complete"}:
                raise ValueError("exact fit-competing schema required")
            result=fit_competing_event_posterior(
                row["rows"],cutoff=row["cutoff"],
                residual_category_id=row["residual_category_id"],
                candidate_universe_complete=row["candidate_universe_complete"])
        elif args.mode=="simulate-competing":
            if set(row)!={"posterior","trials","seed"}:
                raise ValueError("exact simulate-competing schema required")
            result=simulate_competing_posterior_uncertainty(
                row["posterior"],trials=row["trials"],seed=row["seed"])
        elif args.mode=="three-competing":
            if set(row)!={"posteriors","trials","seeds"}:
                raise ValueError("exact three-competing schema required")
            result=run_three_competing_event_scenarios(
                row["posteriors"],trials=row["trials"],seeds=row["seeds"])
        elif args.mode=="fit-binary":
            required={
                "event_definition","prior_alpha","prior_beta","successes","failures",
                "evidence_available_at","cutoff",
            }
            if set(row)!=required:
                raise ValueError("exact fit-binary schema required")
            result=fit_binary_rare_event_posterior(**row)
        else:
            if set(row)!={"posterior","trials","seed"}:
                raise ValueError("exact simulate-binary schema required")
            result=simulate_binary_posterior_uncertainty(
                row["posterior"],trials=row["trials"],seed=row["seed"])
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
