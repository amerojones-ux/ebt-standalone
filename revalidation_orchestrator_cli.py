"""Offline CLI for immutable role/market revalidation orchestration."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.revalidation_orchestrator import (
    assess_revalidation_completion,
    plan_event_revalidation,
    role_state_from_nba_injury,
)


def load(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline Black Diamond revalidation state machine")
    sub=p.add_subparsers(dest="mode",required=True)

    a=sub.add_parser("plan")
    a.add_argument("prior")
    a.add_argument("current_role_state")

    a=sub.add_parser("nba-role-state")
    a.add_argument("canonical_report")
    a.add_argument("injury_diff")
    a.add_argument("game_gate")
    a.add_argument("--event-key",required=True)

    a=sub.add_parser("complete")
    a.add_argument("plan")
    a.add_argument("current_role_gate")
    a.add_argument("rerun_receipt")
    a.add_argument("market_receipt")

    args=p.parse_args(argv)
    try:
        if args.mode=="plan":
            result=plan_event_revalidation(
                load(args.prior),load(args.current_role_state))
        elif args.mode=="nba-role-state":
            result=role_state_from_nba_injury(
                load(args.canonical_report),load(args.injury_diff),load(args.game_gate),
                event_key=args.event_key)
        else:
            result=assess_revalidation_completion(
                load(args.plan),
                current_role_gate=load(args.current_role_gate),
                rerun_receipt=load(args.rerun_receipt),
                market_receipt=load(args.market_receipt))
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
