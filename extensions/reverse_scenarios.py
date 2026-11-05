"""Offline three-scenario reverse-under research gate.

Caller supplies independently built, complete count PMFs. No live verification,
calibration, fitting, Monte Carlo, or wager certification is implied.
"""
from decimal import Decimal
from extensions.underperformance import num, validated_pmf


def scenario_under_diagnostic(mc1_pmf, mc2_pmf, mc3_pmf, line, *,
                              baseline, material_fraction='0.8'):
    """Return distinct exact-under and 20%-shortfall probabilities per scenario.

    MC1/2/3 labels are *scenario slots*, not claims that Monte Carlo ran.
    Never average scenarios or treat a scenario probability as calibrated.
    """
    threshold, normal, fraction = num(line), num(baseline), num(material_fraction)
    if threshold <= 0 or normal <= 0 or not Decimal(0) < fraction < Decimal(1):
        raise ValueError('positive line/baseline and material_fraction in (0,1) required')
    scenarios = {}
    for name, raw in [('MC1_baseline', mc1_pmf), ('MC2_adverse', mc2_pmf),
                      ('MC3_over_friendly', mc3_pmf)]:
        pmf = validated_pmf(raw)
        under = sum((p for y, p in pmf.items() if Decimal(y) < threshold), Decimal(0))
        push = sum((p for y, p in pmf.items() if Decimal(y) == threshold), Decimal(0))
        shortfall = sum((p for y, p in pmf.items()
                         if Decimal(y) <= normal * fraction), Decimal(0))
        scenarios[name] = {
            'modeled_exact_under': float(under),
            'modeled_push': float(push),
            'modeled_material_shortfall': float(shortfall),
        }
    return {
        'mode': 'OFFLINE_SCENARIO_DIAGNOSTIC',
        'scenario_labels_only': True,
        'simulation_status': 'NOT RUN',
        'calibrated_probability': None,
        'certified_85_percent': False,
        'forecast_status': 'HOLD',
        'wager_status': 'NOT APPROVED',
        'line': str(threshold),
        'normal_baseline': str(normal),
        'material_fraction': str(fraction),
        'scenarios': scenarios,
        'minimum_scenario_exact_under': min(
            x['modeled_exact_under'] for x in scenarios.values()),
    }
