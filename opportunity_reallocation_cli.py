"""Offline CLI for beneficiary opportunity-share redistribution."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.opportunity_reallocation import (
    allocate_displaced_opportunity,
    run_reallocation_scenarios,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline beneficiary opportunity-share research")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("allocate")
    a.add_argument("input")

    a=sub.add_parser("scenarios")
    a.add_argument("input")

    args=p.parse_args(argv)
    try:
        row=load(args.input)
        if not isinstance(row,dict):
            raise ValueError("input object required")
        if args.mode=="allocate":
            required={
                "roster","metric","team_budget","cutoff",
                "redistribution_fraction","scenario_name",
            }
            if set(row)!=required:
                raise ValueError("exact allocate schema required")
            result=allocate_displaced_opportunity(
                row["roster"],metric=row["metric"],team_budget=row["team_budget"],
                cutoff=row["cutoff"],redistribution_fraction=row["redistribution_fraction"],
                scenario_name=row["scenario_name"])
        else:
            required={
                "base_roster","scenario_specs","metric","team_budget","cutoff",
            }
            if set(row)!=required:
                raise ValueError("exact scenarios schema required")
            result=run_reallocation_scenarios(
                row["base_roster"],row["scenario_specs"],metric=row["metric"],
                team_budget=row["team_budget"],cutoff=row["cutoff"])
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
