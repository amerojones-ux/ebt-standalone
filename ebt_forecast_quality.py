"""Offline chronological calibration diagnostics and research release checks.

No credentials/network access. Inputs must come from independently verified,
immutable pregame archives; declared timestamps are not proof of such archives.
No function approves a wager or deployment. Half-point count props only.
"""
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timezone
from hashlib import sha256
from math import isfinite, log, sqrt
from statistics import NormalDist
from zoneinfo import ZoneInfo
from decimal import Decimal
import json

VERSION = 'recovery-2026-10-31-v1'
COHORT_FIELDS = ('league', 'market', 'side', 'period', 'threshold_band',
                 'model_version', 'selection_policy')
IDENTITY_FIELDS = ('event_id', 'subject_id', 'market', 'side', 'line', 'period', 'rules_hash')
COUNT_MARKETS = {'PTS','REB','AST','BLK','STL','3PM','FTA','FGM','PTS+AST','REB+AST',
                 'PTS+REB+AST','RUSH_YDS','REC_YDS','PASS_YDS','RECEPTIONS','CARRIES',
                 'SHOTS','SAVES','HITS','STRIKEOUTS','TEAM_PTS','TEAM_GOALS','TOTAL_PTS'}


def clock(s):
    if not isinstance(s, str):
        raise ValueError('Timezone-aware ISO timestamp required')
    try:
        t = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError('Invalid timestamp') from e
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('Timezone-aware ISO timestamp required')
    return t.astimezone(timezone.utc)


def probability(p):
    if type(p) not in (int, float, Decimal) or not isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Finite model probability in [0,1] required')
    return float(p)


def digest(value):
    def canonical(v):
        if type(v) in (float,Decimal):
            d=Decimal(str(v))
            if not d.is_finite():raise ValueError('Nonfinite digest value')
            return str(d.normalize())
        if isinstance(v,dict):return {k:canonical(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [canonical(x) for x in v]
        return v
    return sha256(json.dumps(canonical(value),sort_keys=True,separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def identity(r):
    return tuple(r.get(k) for k in IDENTITY_FIELDS)


def validate_prediction(r):
    for k in set(COHORT_FIELDS + IDENTITY_FIELDS + ('forecast_id', 'archive_ref',)):
        if k != 'line' and (not isinstance(r.get(k), str) or not r[k].strip()):
            raise ValueError('Missing identity/provenance field: ' + k)
    if r['probability_kind'] != 'model_forecast':
        raise ValueError('History percentages, odds and scenario scores are not model forecasts')
    if r['side'] not in ('over', 'under') or r['period'] != 'full_game':
        raise ValueError('Unsupported side/period; use a separate evaluated cohort')
    if r['market'] not in COUNT_MARKETS:
        raise ValueError('Canonical count market required; market aliases need an adapter')
    line = r['line']
    if type(line) not in (float, int, Decimal) or not isfinite(line) or line <= 0 or line % 1 != Decimal('.5'):
        raise ValueError('Positive half-point count line required; pushes need a separate adapter')
    probability(r['p_raw'])
    generated = clock(r['generated_at']); locked = clock(r['locked_at'])
    start = clock(r['event_start'])
    if not clock(r['training_cutoff']) < generated <= locked < start:
        raise ValueError('Training/generation/lock/start chronology invalid')
    times = r.get('source_available_times')
    if not isinstance(times, list) or not times or any(clock(t) > generated for t in times):
        raise ValueError('Missing provenance or future feature/source leakage')
    expected = start.astimezone(ZoneInfo('America/Chicago')).date().isoformat()
    if r.get('slate_date') != expected:
        raise ValueError('Slate date must match America/Chicago event date')
    return tuple(r[k] for k in COHORT_FIELDS)


def validate_final(r):
    validate_prediction(r)
    if r.get('settlement') != 'FINAL':
        raise ValueError('Only verified final nonvoid observations can calibrate this binary adapter')
    if type(r.get('actual')) is not int or r['actual'] < 0:
        raise ValueError('Nonnegative final count required')
    if clock(r['settled_at']) < clock(r['event_start']) or not r.get('result_ref'):
        raise ValueError('Missing final result provenance or invalid settlement time')
    return int(r['actual'] > r['line'] if r['side'] == 'over' else r['actual'] < r['line'])


def chronological_split(rows):
    """Prespecified policy: highest RAW-probability record per event, then date blocks.

    Selection uses no final results. One event contributes at most one observation
    to this conservative calibration experiment. Same-day games stay together.
    """
    rows = list(rows)
    if not rows:
        raise ValueError('No pregame probability archive supplied')
    seen = set(); cohorts = set(); byevent = defaultdict(list)
    for r in rows:
        cohorts.add(validate_prediction(r))
        key = identity(r)
        if key in seen:
            raise ValueError('Duplicate condition across books/boards')
        seen.add(key)
        validate_final(r)
        byevent[r['event_id']].append(r)
    if len(cohorts) != 1:
        raise ValueError('Do not pool different sports, markets, sides, models or policies')
    chosen = []
    for rs in byevent.values():
        if len({(r['event_start'], r['slate_date']) for r in rs}) != 1:
            raise ValueError('Conflicting event identity')
        chosen.append(sorted(rs, key=lambda r: (-r['p_raw'], r['forecast_id']))[0])
    days = sorted({r['slate_date'] for r in chosen})
    if len(days) < 4:
        raise ValueError('Need multiple chronological slate blocks')
    a = max(1, len(days) // 2); b = max(a + 1, 3 * len(days) // 4)
    train = [r for r in chosen if r['slate_date'] < days[a]]
    cal = [r for r in chosen if days[a] <= r['slate_date'] < days[b]]
    test = [r for r in chosen if r['slate_date'] >= days[b]]
    for before, after in ((train, cal), (cal, test)):
        if max(clock(r['settled_at']) for r in before) >= min(clock(r['locked_at']) for r in after):
            raise ValueError('Earlier labels were unavailable at the next block lock')
    return train, cal, test


def fit_isotonic(rows):
    """Pooled-adjacent-violators squared-error fit; ties pooled, step interpolation.

    Fits CALIBRATION records only. This is not a player opportunity model.
    """
    ties = defaultdict(list)
    for r in rows:
        ties[probability(r['p_raw'])].append(validate_final(r))
    if not ties:
        raise ValueError('Empty calibration block')
    blocks = []
    for p, ys in sorted(ties.items()):
        blocks.append([p, p, sum(ys), len(ys)])
        while len(blocks) > 1 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            right = blocks.pop(); left = blocks.pop()
            blocks.append([left[0], right[1], left[2] + right[2], left[3] + right[3]])
    xs = sorted(ties)
    values = [next(s/n for lo, hi, s, n in blocks if lo <= p <= hi) for p in xs]
    return {'x': xs, 'p': values, 'method': 'PAV_step', 'fitted_on': 'calibration_only'}


def calibrated_probability(model, p):
    p = probability(p)
    xs=[probability(x) for x in model['x']]
    if p < xs[0] or p > xs[-1]:
        raise ValueError('Raw probability outside calibration support')
    return probability(model['p'][max(0,bisect_right(xs,p)-1)])


def scores(ps, ys):
    n = len(ys)
    if not n or len(ps) != n:
        raise ValueError('Matched nonempty predictions/outcomes required')
    ps = [probability(p) for p in ps]
    q = [min(1-1e-12, max(1e-12, p)) for p in ps]
    return {'n': n, 'brier': sum((p-y)**2 for p, y in zip(ps, ys))/n,
            'log_loss': -sum(y*log(p)+(1-y)*log(1-p) for p, y in zip(q, ys))/n}


def wilson_lower(hits, n, confidence=.95):
    """One-sided cohort hit-rate bound, not an individual probability interval."""
    if not n:
        return None
    z = NormalDist().inv_cdf(confidence); p = hits/n
    return (p+z*z/(2*n)-z*sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def calibrate_and_test(rows, *, min_calibration=100, min_test=100):
    """Minimum counts and tolerances are provisional operational policy, not proof.

    Base model must already be trained before each locked forecast. Its training
    dataset is not reconstructed here. The early archive block supplies a baseline.
    Test labels are never used to refit the calibrator or select its method.
    """
    for x in (min_calibration, min_test):
        if type(x) is not int or x < 1:
            raise ValueError('Positive sample policy required')
    rows = list(rows)
    train, cal, test = chronological_split(rows)
    model = fit_isotonic(cal); reasons = []
    if len(cal) < min_calibration: reasons.append('insufficient calibration event clusters')
    if len(test) < min_test: reasons.append('insufficient test event clusters')
    ps=[]; ys=[]; supported=[]
    for r in test:
        try: p = calibrated_probability(model, r['p_raw'])
        except ValueError:
            reasons.append('test forecasts outside calibration support'); continue
        supported.append(r); ps.append(p); ys.append(validate_final(r))
    if not supported:
        raise ValueError('No supported untouched test predictions')
    raw = scores([r['p_raw'] for r in supported], ys); adjusted = scores(ps, ys)
    base = (sum(validate_final(r) for r in train)+.5)/(len(train)+1)
    baseline = scores([base]*len(ys), ys)
    if adjusted['brier'] > raw['brier'] + 1e-12 or adjusted['log_loss'] > raw['log_loss'] + 1e-12:
        reasons.append('calibration worsens held-out proper scores')
    if adjusted['brier'] >= baseline['brier'] or adjusted['log_loss'] >= baseline['log_loss']:
        reasons.append('no held-out improvement over early-period constant baseline')
    buckets=[]
    for lo, hi in ((0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.00000001)):
        ix=[i for i,p in enumerate(ps) if lo <= p < hi]
        if not ix: continue
        h=sum(ys[i] for i in ix); n=len(ix); pred=sum(ps[i] for i in ix)/n
        buckets.append({'lower':lo,'upper':min(hi,1),'n_events':n,'mean_predicted':pred,
                        'hit_rate':h/n,'cohort_lower_95':wilson_lower(h,n),
                        'absolute_gap':abs(pred-h/n)})
    ece=sum(b['n_events']*b['absolute_gap'] for b in buckets)/len(ps)
    if ece > .05: reasons.append('held-out reliability gap exceeds provisional 5 percentage points')
    return {'status':'HOLD' if reasons else 'DIAGNOSTICS_PASS_REQUIRES_ARCHIVE_REVIEW',
            'version':VERSION,'wager_approved':False,'cohort':list(validate_prediction(rows[0])),
            'selection_rule':'highest raw probability per event; lexical forecast_id tie break',
            'archive_sha256':digest(rows),'calibrator':model,'calibration_count':len(cal),
            'test_count':len(test),'calibration_ended_at':max((r['settled_at'] for r in cal),key=clock),
            'evaluated_through':max((r['settled_at'] for r in test),key=clock),
            'event_ids':sorted({r['event_id'] for r in rows}),
            'raw_scores':raw,'calibrated_scores':adjusted,'constant_baseline_scores':baseline,
            'reliability':buckets,'ece':ece,'reasons':sorted(set(reasons)),
            'policy':{'min_calibration':min_calibration,'min_test':min_test,'min_bucket_events':100,
                      'cohort_lower_target':.8,'reliability_gap_limit':.05},
            'limitations':['One event per record reduces within-game duplication, not all cross-game dependence.',
                          'Archive provenance requires independent verification; timestamps are declarations.',
                          'Sample policy and observed scores do not prove future accuracy.']}


def assess_release(candidate, report, *, asof, archive_review=None):
    """Do not consume outcomes here. Review must bind the exact diagnostic report.

    Independent archive review is an external evidence dependency, not a boolean
    supplied by a data provider. No local file protects against a dishonest caller.
    """
    reasons=[]; p=None
    try:
        cohort=list(validate_prediction(candidate))
        now=clock(asof)
        if clock(candidate['locked_at']) > now or now >= clock(candidate['event_start']):
            reasons.append('not a currently locked pregame candidate')
        if report['status'] != 'DIAGNOSTICS_PASS_REQUIRES_ARCHIVE_REVIEW':
            reasons.append('calibration diagnostics not passed')
        if cohort != report['cohort']: reasons.append('wrong calibration cohort or model version')
        if candidate['event_id'] in report['event_ids']: reasons.append('event already used for calibration/evaluation')
        if clock(report['evaluated_through']) >= clock(candidate['generated_at']):
            reasons.append('calibration uses information unavailable to this forecast')
        if report['policy']['min_calibration'] < 100 or report['policy']['min_test'] < 100:
            reasons.append('weakened sample policy is diagnostic only')
        p=calibrated_probability(report['calibrator'],candidate['p_raw'])
        b=next((b for b in report['reliability'] if b['lower'] <= p < b['upper'] or p == 1 == b['upper']),None)
        if p < .8: reasons.append('calibrated estimate below 80 percent')
        if not b or b['n_events'] < 100 or b['cohort_lower_95'] < .8 or b['absolute_gap'] > .05:
            reasons.append('80-percent cohort lacks sufficient held-out support')
        if not isinstance(archive_review,dict) or archive_review.get('report_sha256')!=digest(report) or not archive_review.get('review_ref'):
            reasons.append('missing independent archive review bound to this report')
        # A quality gate does not authenticate third-party API data by itself.
        required=('official_identity_ref','official_status_ref','market_snapshot_ref',
                  'rules_ref','opportunity_model_ref','matchup_model_ref','mc1_receipt',
                  'mc2_receipt','mc3_receipt','stress_review_ref')
        for k in required:
            if not isinstance(candidate.get(k),str) or not candidate[k].strip(): reasons.append('missing '+k)
        for k in ('data_conflict','role_restriction_unresolved'):
            if candidate.get(k) is not False: reasons.append(k+' unresolved')
        for k in ('market_snapshot_at','official_status_at'):
            t=clock(candidate[k])
            if t>clock(candidate['locked_at']) or (now-t).total_seconds()>900:
                reasons.append(k+' future or older than provisional 15-minute policy')
        for k in ('mc1_trials','mc2_trials','mc3_trials'):
            if type(candidate.get(k)) is not int or candidate[k] < 250000:
                reasons.append('missing 250k execution evidence: '+k)
    except (ValueError,KeyError,TypeError,StopIteration) as e:
        reasons.append('invalid/missing evidence: '+str(e))
    return {'status':'HOLD' if reasons else 'PASSES_LOCAL_RESEARCH_GATE',
            'wager_approved':False,'calibrated_estimate':p,'reasons':sorted(set(reasons)),
            'notice':'Conditional research eligibility; no deployment or wagering authorization.'}
