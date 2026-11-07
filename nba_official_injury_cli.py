"""Offline CLI for official NBA injury-report validation and rerun gates."""
import argparse
import json
import sys
from pathlib import Path

from ebt_json import strict_json
from extensions.nba_official_injury import (
    assess_game_injury_gate,
    bind_canonical_identities,
    diff_official_reports,
    latest_report_before,
    parse_official_injury_index,
    validate_extracted_report,
)


def _json(path):
    value=strict_json(Path(path).read_text(encoding="utf-8"))
    return value


def main(argv=None):
    parser=argparse.ArgumentParser(
        description="Offline fail-closed NBA official injury-report contracts")
    sub=parser.add_subparsers(dest="mode",required=True)

    p=sub.add_parser("index")
    p.add_argument("html")
    p.add_argument("--cutoff")

    p=sub.add_parser("normalize")
    p.add_argument("rows")
    p.add_argument("--report-url",required=True)
    p.add_argument("--captured-at",required=True)

    p=sub.add_parser("bind")
    p.add_argument("report")
    p.add_argument("--team-ids",required=True)
    p.add_argument("--player-ids",required=True)
    p.add_argument("--event-schedule",required=True)

    p=sub.add_parser("diff")
    p.add_argument("previous")
    p.add_argument("current")

    p=sub.add_parser("gate")
    p.add_argument("report")
    p.add_argument("--event-key",required=True)
    p.add_argument("--cutoff",required=True)
    p.add_argument("--max-report-age-minutes",required=True,type=int)

    args=parser.parse_args(argv)
    try:
        if args.mode=="index":
            html=Path(args.html).read_text(encoding="utf-8")
            result={"reports":parse_official_injury_index(html)}
            if args.cutoff:
                result["latest_before_cutoff"]=latest_report_before(
                    result["reports"],args.cutoff)
        elif args.mode=="normalize":
            rows=_json(args.rows)
            if not isinstance(rows,list):
                raise ValueError("rows JSON array required")
            result=validate_extracted_report(
                rows,report_url=args.report_url,captured_at=args.captured_at)
        elif args.mode=="bind":
            result=bind_canonical_identities(
                _json(args.report),
                team_ids=_json(args.team_ids),
                player_ids=_json(args.player_ids),
                event_schedule=_json(args.event_schedule))
        elif args.mode=="diff":
            result=diff_official_reports(
                _json(args.previous),_json(args.current))
        else:
            result=assess_game_injury_gate(
                _json(args.report),event_key=args.event_key,cutoff=args.cutoff,
                max_report_age_minutes=args.max_report_age_minutes)
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as exc:
        print(json.dumps({
            "status":"HOLD","error":str(exc),"wager_status":"NOT APPROVED"
        }))
        return 2


if __name__=="__main__":
    sys.exit(main())
