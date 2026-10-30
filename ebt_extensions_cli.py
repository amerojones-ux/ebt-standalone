"""Explicit offline CLI entry point for EBT.ai sports research extensions.

No live sources, calibrated approvals, or site-access bypasses are included.
"""
import argparse
import json
import sys
from pathlib import Path
from ebt_json import strict_json
from extensions.underperformance import evaluate_count_under, audit_locked_unders
from extensions.streak_intelligence import import_authorized_streak
from extensions.monte_carlo import three_way_under_mc


def main(argv=None):
    p=argparse.ArgumentParser(description='Offline, fail-closed research extensions')
    sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('under',help='Evaluate already locked count distribution')
    a.add_argument('input',help='JSON object with pmf,line and optional normal_baseline, severe_fraction, over_friendly_pmf')
    a=sub.add_parser('under-mc',help='Run three purpose-distinct offline simulations (>=100k each)')
    a.add_argument('input',help='JSON: pmfs, line, seeds, trials')
    a=sub.add_parser('under-audit',help='Audit immutable pregame under records')
    a.add_argument('input',help='JSON array of pregame-locked forecast records')
    a=sub.add_parser('streak',help='Local operator-attested CSV streak summary')
    a.add_argument('input');a.add_argument('--approval',required=True)
    a.add_argument('--player-id',required=True);a.add_argument('--stat',required=True)
    a.add_argument('--threshold',required=True);a.add_argument('--operator',required=True,choices=('ge','gt','lt'))
    a.add_argument('--as-of-utc',required=True);a.add_argument('--cutoff-date')
    args=p.parse_args(argv)
    try:
        if args.mode=='under':
            row=strict_json(Path(args.input).read_text(encoding='utf-8'))
            if not isinstance(row,dict):
                raise ValueError('under input object required')
            required=('pmf','line')
            if any(k not in row for k in required) or set(row)-set(required)-{'normal_baseline','severe_fraction','over_friendly_pmf'}:
                raise ValueError('unexpected or missing under fields')
            kw={key:row[key] for key in ('normal_baseline','severe_fraction','over_friendly_pmf') if key in row}
            result=evaluate_count_under(row['pmf'],row['line'],**kw)
        elif args.mode=='under-mc':
            row=strict_json(Path(args.input).read_text(encoding='utf-8'))
            if not isinstance(row,dict) or set(row)!={'pmfs','line','seeds','trials'}:
                raise ValueError('exact under-mc input schema required')
            result=three_way_under_mc(row['pmfs'],row['line'],trials=row['trials'],seeds=row['seeds'])
        elif args.mode=='under-audit':
            result=audit_locked_unders(strict_json(Path(args.input).read_text(encoding='utf-8')))
        else:
            result=import_authorized_streak(args.input,approval_path=args.approval,
                                            player_id=args.player_id,stat=args.stat,
                                            threshold=args.threshold,operator=args.operator,
                                            as_of_utc=args.as_of_utc,cutoff_date=args.cutoff_date)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError,OverflowError) as exc:
        print(json.dumps({'status':'HOLD','error':str(exc),'wager_status':'NOT APPROVED'}));return 2

if __name__=='__main__':sys.exit(main())