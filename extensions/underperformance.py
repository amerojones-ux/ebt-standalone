"""Offline count-under probability and historically locked under audit.

No model fitting, sportsbook access, odds anchoring, calibrated claims, or wagering.
Supply complete, independent pre-event probability mass functions (PMFs).
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from math import log


def num(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not a number')
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('finite decimal required') from exc
    if not n.is_finite():
        raise ValueError('finite decimal required')
    return n


def validated_pmf(raw):
    """JSON object may use canonical nonnegative integer keys such as '0'."""
    if not isinstance(raw, dict) or not raw:
        raise ValueError('complete count PMF required')
    out = {}
    for key, mass in raw.items():
        if type(key) is int:
            k = key
        elif isinstance(key, str) and key.isascii() and key.isdecimal() and (key == '0' or not key.startswith('0')):
            k = int(key)
        else:
            raise ValueError('canonical integer outcome key required')
        if k < 0 or k in out:
            raise ValueError('invalid or duplicate PMF outcome')
        p = num(mass)
        if p < 0 or p > 1:
            raise ValueError('invalid PMF mass')
        out[k] = p
    if abs(sum(out.values()) - Decimal(1)) > Decimal('1e-10'):
        raise ValueError('PMF mass must sum to one: do not discard tails')
    return out


def quantile(pmf, fraction):
    q = num(fraction)
    if not 0 < q <= 1:
        raise ValueError('quantile must be in (0,1]')
    accum = Decimal(0)
    for outcome, mass in sorted(pmf.items()):
        accum += mass
        if mass > 0 and accum >= q:
            return outcome
    if abs(accum - 1) <= Decimal('1e-10'):
        return max(k for k,mass in pmf.items() if mass > 0)
    raise ValueError('incomplete PMF')


def evaluate_count_under(pmf, line, *, normal_baseline=None, severe_fraction='0.5', over_friendly_pmf=None):
    """Market under P(Y<L) differs from below-normal and severe underperformance.

    Any whole-number push remains a distinct outcome; DNP/void are not modeled.
    Results are modeled from caller-supplied distribution, never calibrated.
    """
    p = validated_pmf(pmf)
    threshold = num(line)
    if threshold <= 0:
        raise ValueError('positive line required')
    win = sum((v for k, v in p.items() if k < threshold), Decimal(0))
    push = sum((v for k, v in p.items() if k == threshold), Decimal(0))
    lose = sum((v for k, v in p.items() if k > threshold), Decimal(0))
    central = quantile(p, '.5')
    result = {
        'mode': 'OFFLINE_COUNT_UNDER_RESEARCH',
        'forecast_status': 'HOLD', 'wager_status': 'NOT APPROVED',
        'source_verified': False, 'calibration_verified': False,
        'distribution_fitted_by_this_module': False,
        'market_under_probability_modeled': float(win),
        'push_probability_modeled': float(push),
        'market_over_probability_modeled': float(lose),
        'p50': central, 'p80': quantile(p, '.8'), 'p90': quantile(p, '.9'),
        'mean': float(sum((Decimal(k)*v for k,v in p.items()), Decimal(0))),
        'central_under_cushion_units': str(threshold-Decimal(central)),
        'central_under_cushion_percent': float(Decimal(100)*(threshold-Decimal(central))/threshold),
        'simulation_status': 'NOT RUN',
        'not_for': ['live wager approval', 'calibrated probability', 'unverified operator quotes']
    }
    if normal_baseline is not None:
        baseline = num(normal_baseline)
        fraction = num(severe_fraction)
        if baseline <= 0 or not 0 < fraction < 1:
            raise ValueError('positive baseline and predeclared severe fraction (0,1) required')
        result['below_normal_probability_modeled'] = float(sum((v for k,v in p.items() if k < baseline), Decimal(0)))
        result['severe_underperformance_probability_modeled'] = float(sum((v for k,v in p.items() if Decimal(k) <= baseline * fraction), Decimal(0)))
        result['normal_baseline'] = str(baseline)
        result['severe_fraction'] = str(fraction)
    if over_friendly_pmf is not None:
        adverse = validated_pmf(over_friendly_pmf)
        result['over_friendly_recovery_under_probability_modeled'] = float(sum((v for k,v in adverse.items() if k < threshold), Decimal(0)))
        result['adverse_under_cushion_units'] = str(threshold-Decimal(quantile(adverse,'.5')))
    return result


def _clock(value):
    if not isinstance(value, str):
        raise ValueError('time string required')
    try:
        x = datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('invalid time') from exc
    if x.tzinfo is None or x.utcoffset() is None:
        raise ValueError('timezone-aware time required')
    return x.astimezone(timezone.utc)


def audit_locked_unders(rows):
    """Diagnostics, not certification: requires verifiable, pregame-locked records.

    All pregame published thresholds remain in denominator; PENDING/VOID separate.
    Half-integer lines only to avoid operator-specific whole-line push ambiguity.
    """
    if not isinstance(rows, list):
        raise ValueError('array required')
    seen = set(); scored = []; pending = []; brier = []; loss = []
    for record in rows:
        if not isinstance(record, dict):
            raise ValueError('record object required')
        key = (record['event_id'],record['player_id'],record['stat'],
               num(record['line']),record.get('period','full_game'))
        if key in seen:
            raise ValueError('duplicate forecast identity')
        seen.add(key)
        if record.get('probability_kind') != 'model_forecast':
            raise ValueError('explicit model_forecast probability kind required; streaks and odds are not forecasts')
        locked, start = _clock(record['locked_at']), _clock(record['event_start'])
        if locked >= start:
            raise ValueError('forecast must be locked pregame')
        stamps = record.get('source_available_times')
        if not isinstance(stamps, list) or not stamps or any(_clock(s)>locked for s in stamps):
            raise ValueError('missing or post-lock evidence')
        probability = num(record['p_under'])
        threshold = num(record['line'])
        if not 0 <= probability <= 1 or threshold <= 0 or threshold%1 != Decimal('.5'):
            raise ValueError('probability or half-integer count threshold invalid')
        settlement = record['settlement']
        if settlement not in ('FINAL','PENDING','VOID'):
            raise ValueError('unsupported settlement')
        if settlement != 'FINAL':
            pending.append({'id':record['forecast_id'],'status':settlement}); continue
        if record.get('result_verified') is not True:
            pending.append({'id':record['forecast_id'],'status':'UNVERIFIED_FINAL'}); continue
        y = record.get('actual')
        if type(y) is not int or y < 0:
            raise ValueError('final count integer required')
        hit = int(Decimal(y) < threshold)
        brier.append(float((probability-hit)**2))
        # Clamp only for finite log-loss reporting, never alter stored probability.
        q = max(1e-12,min(1-1e-12,float(probability)))
        loss.append(-log(q if hit else 1-q))
        scored.append({'id':record['forecast_id'],'hit':bool(hit),'p_under':float(probability)})
    return {'mode':'LOCKED_UNDER_AUDIT_DIAGNOSTIC','status':'RESEARCH ONLY',
            'n_settled_verified':len(scored),'n_pending_or_void':len(pending),
            'records':scored,'excluded':pending,
            'brier':sum(brier)/len(brier) if brier else None,
            'log_loss':sum(loss)/len(loss) if loss else None,
            'certified_calibration':False,'model_weights_changed':False}
