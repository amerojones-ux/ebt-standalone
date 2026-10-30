"""Three reproducible, research-only count-under Monte Carlo diagnostics.

Requires caller-supplied independent pregame PMFs. The three samples do NOT
establish independent-source evidence, input fit, calibration, or joint parlays.
"""
import bisect
import hashlib
import inspect
import json
import random
from decimal import Decimal
from pathlib import Path
from .underperformance import validated_pmf, num

PURPOSES=('baseline','adversarial','scenario')


def three_way_under_mc(pmf_by_purpose, line, *, trials=100000, seeds=None):
    """MC-1 baseline, MC-2 adversarial, MC-3 alternate scenario distributions.

    The scenario here is a SINGLE-outcome sensitivity run, NOT a dependent
    multi-player joint Monte Carlo. Provider/role verification is external.
    """
    if not isinstance(pmf_by_purpose, dict) or set(pmf_by_purpose)!=set(PURPOSES):
        raise ValueError('all three purpose-specific complete PMFs required')
    if type(trials) is not int or not 100000 <= trials <= 2000000:
        raise ValueError('100000..2000000 Monte Carlo trials required')
    if not isinstance(seeds, dict) or set(seeds)!=set(PURPOSES) or any(type(v) is not int or not 0<=v<2**63 for v in seeds.values()):
        raise ValueError('three distinct integer run seeds required')
    if len(set(seeds.values()))!=3:
        raise ValueError('purpose seeds must be distinct')
    threshold=num(line)
    if threshold<=0:raise ValueError('positive line required')
    code_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    outputs={}
    for purpose in PURPOSES:
        pmf=validated_pmf(pmf_by_purpose[purpose]); sorted_items=sorted(pmf.items())
        outcomes=[k for k,_ in sorted_items]; cumulative=[];s=0.0
        for _,p in sorted_items:
            s+=float(p);cumulative.append(s)
        cumulative[-1]=1.0
        rng=random.Random(seeds[purpose]);wins=pushes=0
        for _ in range(trials):
            obs=outcomes[bisect.bisect_left(cumulative,rng.random())]
            wins+=obs<threshold
            pushes+=obs==threshold
        canon={'pmf':[(k,str(v)) for k,v in sorted_items],'line':str(threshold),'purpose':purpose}
        input_sha=hashlib.sha256(json.dumps(canon,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        outputs[purpose]={'trials':trials,'hits':wins,'pushes':pushes,'misses':trials-wins-pushes,
                          'modeled_hit_rate':wins/trials,'seed':seeds[purpose],
                          'input_sha256':input_sha,'code_sha256':code_sha,
                          'simulation_kind':'PREDECLARED_COUNT_PMF_RESEARCH'}
    return {'mode':'OFFLINE_THREE_WAY_UNDER_MC', 'forecast_status':'HOLD',
            'wager_status':'NOT APPROVED','source_verified':False,
            'calibration_verified':False,'joint_parlay_test_performed':False,
            'purpose_specific_input_distributions_supplied_by_caller':True,
            'runs':outputs,
            'warning':'MC confirms code sampling only; it cannot certify distributions, true player role, correlation, calibrated probability, live odds or EV.'}