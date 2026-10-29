"""Offline sports validation primitives. No network, forecasts or wagers."""
import hashlib,json,math
import os,fcntl
from decimal import Decimal
from fractions import Fraction
from datetime import datetime,timezone

def clock(value):
    if not isinstance(value,str):raise ValueError('timestamp string required')
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None or d.utcoffset() is None: raise ValueError('timezone required')
    return d.astimezone(timezone.utc)

def number(x):
    if isinstance(x,bool): raise ValueError('boolean is not numeric')
    n=Decimal(str(x))
    if not n.is_finite(): raise ValueError('finite value required')
    return n

def probability(x):
    return float(exact_probability(x))

def exact_probability(x):
    p=number(x)
    if not 0<=p<=1: raise ValueError('probability outside [0,1]')
    return p

def settle(actual,threshold,comparator,*,final,participated,void_rule_verified=False):
    if comparator not in ('GE','GT','LT'): raise ValueError('unsupported comparator')
    if final is not True:return 'PENDING'
    if participated is not True:return 'VOID' if participated is False and void_rule_verified is True else 'PENDING'
    if actual is None:return 'PENDING'
    a,t=number(actual),number(threshold)
    if comparator=='GE':return 'HIT' if a>=t else 'MISS'
    if a==t:return 'PUSH'
    return 'HIT' if (a>t if comparator=='GT' else a<t) else 'MISS'

def cushion(median,threshold,direction):
    if direction not in ('OVER','UNDER'):raise ValueError('invalid direction')
    m,t=number(median),number(threshold)
    units=m-t if direction=='OVER' else t-m
    return {'units':str(units),'relative':str(units/abs(t)) if t else None}

EVIDENCE=('identity_verified','active_verified','role_verified','history_verified','distribution_locked','calibration_verified','stress_gates_passed','scenario_gates_passed','uncertainty_verified','engine_mapping_verified')

def qualify(row,*,now,max_quote_age_seconds):
    """Caller must substantiate flags. This checks gates; it does not verify sources."""
    if type(max_quote_age_seconds) is not int or max_quote_age_seconds<=0:raise ValueError('explicit positive quote-age policy required')
    n=clock(now);issues=[]
    if not isinstance(row,dict):return {'forecast':'HOLD','wager':'NOT APPROVED','issues':['invalid_record']}
    if row.get('official_out') is True:return {'forecast':'REJECT','wager':'NOT APPROVED','issues':['official_out']}
    for k in EVIDENCE:
        if row.get(k) is not True:issues.append(k)
    try:
        issued,event,locked=map(clock,(row['issued_at'],row['event_start'],row['model_locked_at']))
        if not locked<=issued<=n<event:issues.append('pregame_time_order')
        if clock(row['calibration_training_end'])>=locked:issues.append('calibration_leakage')
        if not isinstance(row.get('market_key'),str) or not row['market_key'].strip():issues.append('market_identity')
        p,lo=exact_probability(row['calibrated_p']),exact_probability(row['lower_bound'])
        if lo>p or p<Decimal('.87') or lo<Decimal('.80'):issues.append('calibrated_probability_gate')
        if number(row['central_cushion'])<=0 or number(row['adverse_cushion'])<=0:issues.append('cushion_gate')
        for purpose in ('baseline','adversarial','scenario'):
            run=row['runs'][purpose]
            trials=run['trials'];hits=run['hits']
            if type(trials) is not int or trials<100000 or type(hits) is not int or not 0<=hits<=trials:issues.append('trials_'+purpose)
            for key in ('input_sha256','code_sha256'):
                h=run.get(key,'')
                if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):issues.append('provenance_'+purpose)
            if type(run.get('seed')) is not int:issues.append('seed_'+purpose)
    except (KeyError,ValueError,TypeError,AttributeError,ArithmeticError):issues.append('missing_or_invalid_forecast_input')
    forecast='BLACK DIAMOND FORECAST — VALIDATED' if not issues else 'HOLD'
    wager_issues=[]
    try:
        q=row['quote']
        if q.get('operator_verified') is not True: wager_issues.append('operator_quote')
        if q['market_key']!=row['market_key']:wager_issues.append('quote_market_identity')
        age=(n-clock(q['retrieved_at'])).total_seconds()
        if not 0<=age<=max_quote_age_seconds:wager_issues.append('quote_freshness')
        if clock(q['retrieved_at'])<clock(row['model_locked_at']):wager_issues.append('market_before_model_lock')
        raw_odds=number(q['decimal_odds'])
        odds=Fraction(raw_odds)
        if not math.isfinite(float(raw_odds)) or odds<=1 or row.get('settlement_rules_verified') is not True: wager_issues.append('price_or_rules')
        win,push,loss=(Fraction(exact_probability(row[k])) for k in ('win_p','push_p','loss_p'))
        if win+push+loss!=1 or win!=Fraction(exact_probability(row['calibrated_p'])):wager_issues.append('probability_semantics')
        if win*(odds-1)-loss<=0:wager_issues.append('nonpositive_ev')
    except (KeyError,ValueError,TypeError,AttributeError,ArithmeticError):wager_issues.append('missing_or_invalid_quote')
    return {'forecast':forecast,'wager':'APPROVED' if not issues and not wager_issues else 'NOT APPROVED','issues':issues+wager_issues}

def evaluate_holdout(rows):
    """Score externally certified, locked binary outcomes; does not certify calibration."""
    if not rows:raise ValueError('empty evaluation')
    seen=set();scored=[]
    for r in rows:
        if not isinstance(r,dict):raise ValueError('holdout record must be an object')
        key=r['forecast_id']
        if not isinstance(key,str) or not key.strip():raise ValueError('nonempty forecast_id required')
        if key in seen:raise ValueError('duplicate forecast_id')
        seen.add(key)
        if r.get('certified') is not True:raise ValueError('uncertified outcome')
        if not clock(r['training_end'])<clock(r['issued_at'])<clock(r['event_start'])<=clock(r['outcome_available_at']):raise ValueError('temporal leakage')
        if r['result'] not in ('HIT','MISS'):raise ValueError('separate push/void/pending outcomes')
        p=probability(r['p']);y=int(r['result']=='HIT');scored.append((p,y))
    log_terms=[-math.log(p if y else 1-p) if 0<(p if y else 1-p)<=1 else math.inf for p,y in scored]
    return {'n':len(scored),'brier':sum((p-y)**2 for p,y in scored)/len(scored),'log_loss':sum(log_terms)/len(scored),'calibration_certified':False}

def record_hash(record):
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_chain(records):
    last='0'*64;ids=set()
    for r in records:
        if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not r['id'].strip():raise ValueError('invalid ledger record')
        if r['id'] in ids or r['previous_sha256']!=last:raise ValueError('chain discontinuity or duplicate id')
        ids.add(r['id']);expected=record_hash({k:v for k,v in r.items() if k!='sha256'})
        if r['sha256']!=expected:raise ValueError('record tampering')
        last=expected
    return last

def append_record(path,record_id,payload,*,expected_last_sha256):
    """Linux local append only; caller retains the last trusted hash externally."""
    if not isinstance(record_id,str) or not record_id.strip():raise ValueError('record id required')
    with open(path,'a+',encoding='utf-8') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        handle.seek(0);text=handle.read()
        if text and not text.endswith('\n'):raise ValueError('incomplete ledger tail')
        records=[json.loads(line) for line in text.splitlines()]
        last=validate_chain(records)
        if last!=expected_last_sha256:raise ValueError('stale or truncated ledger')
        if any(r['id']==record_id for r in records):raise ValueError('duplicate record id')
        record={'id':record_id,'previous_sha256':last,'payload':payload}
        record['sha256']=record_hash(record)
        encoded=json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n'
        handle.seek(0,2);handle.write(encoded);handle.flush();os.fsync(handle.fileno())
        return record['sha256']
