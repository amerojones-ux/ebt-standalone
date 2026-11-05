"""Offline Bayesian opportunity-efficiency count model (research only).

Input rows must be verified and pre-event; this module cannot verify provenance.
No sportsbook lines used for fitting. No calibration or wagering claims.
"""
from math import comb, lgamma, exp
from .underperformance import num, validated_pmf


def beta_binomial_pmf(opportunities, successes, failures, *, prior_alpha=1, prior_beta=1):
    """Posterior predictive for integer successes given fixed future opportunities.

    successes/failures are historical per-opportunity counts. A shared latent
    conversion rate produces beta-binomial overdispersion versus plug-in binomial.
    """
    if any(type(x) is not int or x < 0 for x in (opportunities, successes, failures)):
        raise ValueError('nonnegative integer counts required')
    if opportunities > 10000:
        raise ValueError('opportunity count exceeds offline safety limit')
    a, b = float(num(prior_alpha)), float(num(prior_beta))
    if a <= 0 or b <= 0:
        raise ValueError('positive priors required')
    a += successes; b += failures
    log_base = lgamma(a + b) - lgamma(a) - lgamma(b)
    out = {}
    for k in range(opportunities + 1):
        lp = (lgamma(opportunities + 1) - lgamma(k + 1)
              - lgamma(opportunities - k + 1)
              + lgamma(k + a) + lgamma(opportunities - k + b)
              - lgamma(opportunities + a + b) + log_base)
        out[str(k)] = exp(lp)
    total = sum(out.values())
    if total <= 0:
        raise ValueError('numerically unstable distribution')
    return {k: v / total for k, v in out.items()}


def mixture_opportunity_pmf(opportunity_weights, successes, failures, *,
                            prior_alpha=1, prior_beta=1):
    """Integrate discrete future-opportunity uncertainty without dropping tails."""
    if not isinstance(opportunity_weights, dict) or not opportunity_weights:
        raise ValueError('complete opportunity distribution required')
    weights = validated_pmf(opportunity_weights)
    out = {}
    for n, weight in weights.items():
        conditional = beta_binomial_pmf(
            n, successes, failures, prior_alpha=prior_alpha, prior_beta=prior_beta)
        for k, probability in conditional.items():
            out[k] = out.get(k, 0.0) + float(weight) * probability
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


def validate_shared_opportunity_budget(player_allocations, team_budget):
    """Enforce a fixed shared budget; not yet a stochastic joint simulator."""
    if not isinstance(player_allocations, dict) or not player_allocations:
        raise ValueError('player allocations required')
    if type(team_budget) is not int or team_budget < 0:
        raise ValueError('nonnegative integer team budget required')
    if any(type(v) is not int or v < 0 for v in player_allocations.values()):
        raise ValueError('nonnegative integer player allocations required')
    if sum(player_allocations.values()) != team_budget:
        raise ValueError('player allocations must exactly equal team budget')
    return True
