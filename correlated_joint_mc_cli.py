"""Offline CLI for correlated combo and dependency-preserving joint MC."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.correlated_joint_mc import (
    compare_combo_correlated_vs_independent,
    decompose_combo_leg,
    run_final_joint_parlay_mc,
    run_three_scenario_joint_mc,
    simulate_joint_model,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline correlated combo/joint MC research")
    sub=p.add_subparsers(dest="mode",required=True)
    for name in ("decompose","simulate","compare-combo","three-scenario","final-joint"):
        a=sub.add_parser(name)
        a.add_argument("input")
    args=p.parse_args(argv)
    try:
        row=load(args.input)
        if not isinstance(row,dict):
            raise ValueError("input object required")
        if args.mode=="decompose":
            if set(row)!={"model","leg"}:
                raise ValueError("exact decompose schema required")
            result=decompose_combo_leg(row["model"],row["leg"])
        elif args.mode=="simulate":
            if set(row)!={"model","legs","trials","seed","label"}:
                raise ValueError("exact simulate schema required")
            result=simulate_joint_model(
                row["model"],row["legs"],trials=row["trials"],
                seed=row["seed"],label=row["label"])
        elif args.mode=="compare-combo":
            if set(row)!={"model","leg","trials","correlated_seed","independent_seed"}:
                raise ValueError("exact compare-combo schema required")
            result=compare_combo_correlated_vs_independent(
                row["model"],row["leg"],trials=row["trials"],
                correlated_seed=row["correlated_seed"],
                independent_seed=row["independent_seed"])
        elif args.mode=="three-scenario":
            if set(row)!={"models","legs","trials","seeds"}:
                raise ValueError("exact three-scenario schema required")
            result=run_three_scenario_joint_mc(
                row["models"],row["legs"],trials=row["trials"],seeds=row["seeds"])
        else:
            if set(row)!={"model","legs","scenario_receipt","trials","seed"}:
                raise ValueError("exact final-joint schema required")
            result=run_final_joint_parlay_mc(
                row["model"],row["legs"],row["scenario_receipt"],
                trials=row["trials"],seed=row["seed"])
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
