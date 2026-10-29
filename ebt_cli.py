"""Offline JSON/CSV review; never fetches data or publishes decisions."""
import argparse,csv,hashlib,io,json,sys
from decimal import Decimal
from pathlib import Path
from collections import Counter,defaultdict
from ebt_validation import qualify,evaluate_holdout

def strict_json(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite JSON number: '+value)
    return json.loads(text,object_pairs_hook=unique,parse_constant=invalid,parse_float=Decimal)

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
    args=p.parse_args(argv)
    try:
        if args.mode=='archive':result=archive_report(args.input)
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
