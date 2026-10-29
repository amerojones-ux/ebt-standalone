"""Offline JSON/CSV review; never fetches data or publishes decisions."""
import argparse,csv,hashlib,io,json,sys
from pathlib import Path
from collections import Counter,defaultdict
from ebt_validation import qualify,evaluate_holdout
from ebt_evidence import ingest
from ebt_json import strict_json
from ebt_collect import collect,extract,verify_extraction
from ebt_calibration import assessment

def archive_report(path):
    raw=Path(path).read_bytes()
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),strict=True)
    headers=reader.fieldnames
    if not headers or len(set(headers))!=len(headers):raise ValueError('missing or duplicate CSV columns')
    try:rows=list(reader)
    except csv.Error as error:raise ValueError('invalid CSV syntax') from error
    required={'date','card_version','selection','threshold','rechecked_result','source_primary'}
    if not rows or not required.issubset(rows[0]):raise ValueError('missing archive columns or empty archive')
    seen=set();duplicates=[];boards=defaultdict(list)
    for i,r in enumerate(rows,2):
        if None in r or any(v is None for v in r.values()):raise ValueError('CSV row width mismatch at record '+str(i))
        if any(not r[k].strip() for k in ('date','card_version','selection','threshold')):raise ValueError('missing archive identity at record '+str(i))
        key=tuple(r[k] for k in ('date','card_version','selection','threshold'))
        if key in seen:duplicates.append(i)
        seen.add(key);boards[r['card_version']].append(r)
    return {'mode':'ARCHIVE_STRUCTURE_REVIEW','input_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'duplicate_rows':duplicates,'boards':{k:{'rows':len(v),'recorded_status_counts':dict(Counter(x['rechecked_result'] for x in v))} for k,v in boards.items()},'independent_outcome_verification_performed':False,'certified_hit_rate':None,'calibration_certified':False,'notes':['Recorded outcomes and URLs preserved as claims; this run does not verify their truth.','Do not combine overlapping board rates or score pending rows as losses.']}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('archive');a.add_argument('input')
    a=sub.add_parser('qualify');a.add_argument('input');a.add_argument('--now',required=True);a.add_argument('--max-quote-age-seconds',type=int,required=True)
    a=sub.add_parser('holdout');a.add_argument('input')
    a=sub.add_parser('evidence');a.add_argument('input');a.add_argument('--requirements',required=True);a.add_argument('--raw-root',required=True);a.add_argument('--cutoff',required=True);a.add_argument('--max-age-seconds',type=int,required=True);a.add_argument('--policy',default=str(Path(__file__).parent/'config'/'source_policy.json'))
    a=sub.add_parser('collect');a.add_argument('url');a.add_argument('--destination',required=True);a.add_argument('--timeout',type=int,default=10)
    a=sub.add_parser('extract');a.add_argument('input');a.add_argument('--raw-root',required=True);a.add_argument('--parameters',required=True);a.add_argument('--verify-claim')
    a=sub.add_parser('calibrate');a.add_argument('input');a.add_argument('--validation',required=True);a.add_argument('--settings',required=True)
    args=p.parse_args(argv)
    try:
        if args.mode=='archive':result=archive_report(args.input)
        elif args.mode=='evidence':
            result=ingest(strict_json(Path(args.input).read_text()),strict_json(Path(args.requirements).read_text()),raw_root=args.raw_root,cutoff=args.cutoff,max_age_seconds=args.max_age_seconds,policy=strict_json(Path(args.policy).read_text()))
        elif args.mode=='collect':result=collect(args.url,args.destination,timeout=args.timeout)
        elif args.mode=='extract':
            receipt=strict_json(Path(args.input).read_text());parameters=strict_json(Path(args.parameters).read_text())
            result=extract(receipt,args.raw_root,parameters=parameters)
            if args.verify_claim:
                claim=strict_json(Path(args.verify_claim).read_text())
                result={'extraction_matches':verify_extraction(receipt,args.raw_root,claim,parameters),'source_truth_verified':False,'forecast_approved':False}
        elif args.mode=='calibrate':result=assessment(strict_json(Path(args.input).read_text()),strict_json(Path(args.validation).read_text()),**strict_json(Path(args.settings).read_text()))
        else:
            rows=strict_json(Path(args.input).read_text())
            if not isinstance(rows,list):raise ValueError('JSON array required')
            if args.mode=='holdout':
                result=evaluate_holdout(rows)
                if not __import__('math').isfinite(result['log_loss']):result.update(log_loss=None,log_loss_infinite=True)
            else:result={'mode':'CALLER_ASSERTED_GATE_CHECK','independent_source_verification_performed':False,'results':[qualify(r,now=args.now,max_quote_age_seconds=args.max_quote_age_seconds) for r in rows]}
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ValueError,TypeError,KeyError,ArithmeticError,OSError) as error:
        print(json.dumps({'status':'HOLD','error':str(error)},allow_nan=False));return 2
if __name__=='__main__':sys.exit(main())
