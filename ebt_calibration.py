"""Temporal isotonic calibration candidates; never self-certify a live model."""
import hashlib,json
from bisect import bisect_left
from fractions import Fraction
from ebt_validation import clock,exact_probability,evaluate_holdout

SCOPE=('competition','market','threshold_type','model_version')

def validate_rows(rows,scope,deadline):
    if not isinstance(rows,list):raise ValueError('forecast row array required')
    seen=set();events=set();validated=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('certified') is not True:raise ValueError('independently certified outcome required')
        if any(row.get(k)!=scope[k] for k in SCOPE):raise ValueError('calibration scope mismatch')
        for k in ('forecast_id','event_id'):
            if not isinstance(row.get(k),str) or not row[k].strip():raise ValueError('canonical forecast/event identity required')
        if row['forecast_id'] in seen:raise ValueError('duplicate forecast_id')
        seen.add(row['forecast_id'])
        if row['event_id'] in events:raise ValueError('one prospectively selected forecast per event required; do not inflate calibration with alternate lines')
        events.add(row['event_id'])
        if row.get('probability_kind') not in (None,'model_forecast'):raise ValueError('descriptive frequencies are not forecast probabilities')
        if row['result'] not in ('HIT','MISS'):raise ValueError('push/void/pending outcomes require separate accounting')
        if not clock(row['training_end'])<clock(row['issued_at'])<clock(row['event_start'])<=clock(row['outcome_available_at'])<=clock(deadline):raise ValueError('temporal leakage or outcome beyond cutoff')
        exact_probability(row['p']);validated.append(row)
    return validated

def fit_blocks(rows):
    groups={}
    for row in rows:
        p=Fraction(exact_probability(row['p']));n,w=groups.get(p,(0,0));groups[p]=(n+1,w+(row['result']=='HIT'))
    blocks=[]
    for p,(n,w) in sorted(groups.items()):
        blocks.append({'upper':p,'count':n,'wins':w})
        while len(blocks)>1 and blocks[-2]['wins']*blocks[-1]['count']>blocks[-1]['wins']*blocks[-2]['count']:
            right=blocks.pop();left=blocks.pop();blocks.append({'upper':right['upper'],'count':left['count']+right['count'],'wins':left['wins']+right['wins']})
    return [{'upper_numerator':str(b['upper'].numerator),'upper_denominator':str(b['upper'].denominator),'count':b['count'],'wins':b['wins']} for b in blocks]

def calibrated_probability(blocks,p):
    return predict(compile_blocks(blocks),p)

def compile_blocks(blocks):
    if not blocks:raise ValueError('fitted blocks required')
    upper=[];values=[]
    for block in blocks:
        bound=Fraction(int(block['upper_numerator']),int(block['upper_denominator']))
        if not 0<=bound<=1 or (upper and bound<=upper[-1]) or type(block['count']) is not int or block['count']<=0 or type(block['wins']) is not int or not 0<=block['wins']<=block['count']:raise ValueError('invalid isotonic blocks')
        upper.append(bound);values.append(Fraction(block['wins'],block['count']))
    if values!=sorted(values):raise ValueError('nonmonotone calibration map')
    return upper,values

def predict(compiled,p):
    upper,values=compiled;index=min(bisect_left(upper,Fraction(exact_probability(p))),len(values)-1)
    return values[index]

def reliability(rows,blocks=None):
    buckets={};compiled=compile_blocks(blocks) if blocks else None
    for row in rows:
        p=predict(compiled,row['p']) if compiled else Fraction(exact_probability(row['p']))
        index=min(int(p*10),9);bucket=buckets.setdefault(index,{'count':0,'predicted_sum':Fraction(0),'hits':0})
        bucket['count']+=1;bucket['predicted_sum']+=p;bucket['hits']+=row['result']=='HIT'
    return [{'lower':i/10,'upper':(i+1)/10,'count':b['count'],'mean_p':float(b['predicted_sum']/b['count']),'hit_rate':b['hits']/b['count']} for i,b in sorted(buckets.items())]

def assessment(training,validation,*,scope,fit_at,assessed_at,policy):
    """All policy minima are research controls, not proof of sufficient calibration."""
    base={'calibration_certified':False,'forecast_approved':False,'scope':scope,'fit_at':fit_at,'assessed_at':assessed_at}
    try:
        if not isinstance(scope,dict) or any(not isinstance(scope.get(k),str) or not scope[k].strip() for k in SCOPE):raise ValueError('complete predeclared scope required')
        if not clock(fit_at)<clock(assessed_at):raise ValueError('assessment must follow fit cutoff')
        keys=('min_training_rows','min_validation_rows','min_training_events','min_validation_events')
        if not isinstance(policy,dict) or not isinstance(policy.get('version'),str) or any(type(policy.get(k)) is not int or policy[k]<2 for k in keys):raise ValueError('versioned positive predeclared research minima required')
        train=validate_rows(training,scope,fit_at);test=validate_rows(validation,scope,assessed_at)
        train_events={r['event_id'] for r in train};test_events={r['event_id'] for r in test}
        counts={'training_rows':len(train),'validation_rows':len(test),'training_events':len(train_events),'validation_events':len(test_events)}
        if any(counts[k.removeprefix('min_')]<policy[k] for k in keys):return {**base,'status':'HOLD','reason':'insufficient certified temporal sample','counts':counts,'policy':policy}
        if train_events&test_events or {r['forecast_id'] for r in train}&{r['forecast_id'] for r in test}:raise ValueError('training/validation overlap')
        if any(clock(r['issued_at'])<=clock(fit_at) for r in test):raise ValueError('validation forecast issued before calibration fit')
        blocks=fit_blocks(train);compiled=compile_blocks(blocks)
        scored=[]
        for row in test:
            # evaluate_holdout accepts Decimal, not Fraction: score exact fractions directly below.
            scored.append((predict(compiled,row['p']),row['result']=='HIT'))
        import math
        def loss(p,y):
            q=p if y else 1-p
            if q==0:return math.inf
            return -math.log1p(-float(1-q)) if q>Fraction(1,2) else math.log(q.denominator)-math.log(q.numerator)
        losses=[loss(p,y) for p,y in scored]
        calibrated={'n':len(scored),'brier':sum(float((p-y)**2) for p,y in scored)/len(scored),'log_loss':sum(losses)/len(losses)}
        raw=evaluate_holdout(test)
        for metric in (raw,calibrated):
            if not math.isfinite(metric['log_loss']):metric.update(log_loss=None,log_loss_infinite=True)
        digest=hashlib.sha256(json.dumps(train,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
        return {**base,'status':'RESEARCH_FIT_EVALUATED','policy':policy,'counts':counts,'training_sha256':digest,'blocks':blocks,'heldout_raw':raw,'heldout_calibrated':calibrated,'reliability_raw':reliability(test),'reliability_calibrated':reliability(test,blocks),'limitations':['Certified flags must be independently substantiated.','Selection bias, clustering uncertainty, regime drift and deployment acceptance require separate review.','No live probability or model gate is automatically changed.']}
    except (KeyError,TypeError,ValueError,ArithmeticError) as error:return {**base,'status':'HOLD','reason':str(error)}
