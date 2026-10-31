"""Offline archive diagnostics only; never fetch data, deploy or place a wager."""
import argparse,json,sys
from pathlib import Path
from decimal import Decimal
from ebt_json import strict_json
from ebt_forecast_quality import calibrate_and_test,assess_release


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('calibrate');a.add_argument('archive')
    a=s.add_parser('assess');a.add_argument('forecast');a.add_argument('--report',required=True)
    a.add_argument('--review');a.add_argument('--asof',required=True)
    args=p.parse_args(argv)
    def read(name):return strict_json(Path(name).read_text())
    try:
        if args.mode=='calibrate':result=calibrate_and_test(read(args.archive))
        else:result=assess_release(read(args.forecast),read(args.report),asof=args.asof,
                                  archive_review=read(args.review) if args.review else None)
        print(json.dumps(result,indent=2,allow_nan=False,default=lambda x:str(x) if isinstance(x,Decimal) else None))
        return 0 if result['status']!='HOLD' else 2
    except (ValueError,TypeError,KeyError,OSError,ArithmeticError) as e:
        print(json.dumps({'status':'HOLD','wager_approved':False,'error':str(e)}));return 2


if __name__=='__main__':sys.exit(main())
