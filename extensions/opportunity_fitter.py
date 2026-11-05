"""Leakage-safe opportunity/efficiency fitting from validated historical rows.

This module does not verify providers, calibrate probabilities, simulate joint
player outcomes, or approve wagers. It expects rows that have already passed
IngestionValidator for the relevant forecast cutoff.
"""
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from .data_ingestion import IngestionValidator, ValidatedObservation
from .trusted_sources import TrustedSourcePolicy
from .opportunity_efficiency import mixture_opportunity_pmf
from .underperformance import num, validated_pmf


class OpportunityEfficiencyFitter:
    def __init__(self, global_opportunity_pmf, *, trusted_source_policy,
                 prior_alpha='1', prior_beta='1', shrinkage_games=8):
        if not isinstance(trusted_source_policy, TrustedSourcePolicy):
            raise ValueError('TrustedSourcePolicy required')
        self.trusted_source_policy = trusted_source_policy
        self.global_opportunity_pmf = validated_pmf(global_opportunity_pmf)
        self.prior_alpha = num(prior_alpha)
        self.prior_beta = num(prior_beta)
        if self.prior_alpha <= 0 or self.prior_beta <= 0:
            raise ValueError('positive efficiency priors required')
        if type(shrinkage_games) is not int or shrinkage_games < 0:
            raise ValueError('shrinkage_games must be a nonnegative integer')
        self.shrinkage_games = shrinkage_games

    def _conversion_rows(self, observations: Iterable[ValidatedObservation]) -> List[ValidatedObservation]:
        rows = list(observations)
        if any(not isinstance(v, ValidatedObservation) for v in rows):
            raise ValueError('ValidatedObservation rows required')
        for v in rows:
            if IngestionValidator.generate_record_hash(v.observation) != v.record_hash:
                raise ValueError('validated observation record hash mismatch')
            if not self.trusted_source_policy.verify_validation_receipt_signature(
                    v.record_hash, v.forecast_cutoff, v.validation_signature_hmac_sha256):
                raise ValueError('validated observation receipt signature invalid')
            if v.observation.outcome_available_at >= v.forecast_cutoff:
                raise ValueError('validated observation violates historical cutoff')
            if v.observation.outcome_semantics != 'successes_of_opportunities':
                raise ValueError('beta-binomial fitter only accepts successes_of_opportunities rows')
        return rows

    def fit_opportunity_pmf(self, observations: Iterable[ValidatedObservation]) -> Dict[str, float]:
        rows = self._conversion_rows(observations)
        empirical = {}
        for row in rows:
            n = row.observation.opportunity_count
            empirical[n] = empirical.get(n, 0) + 1

        n = len(rows)
        if n == 0:
            return {str(k): float(v) for k, v in self.global_opportunity_pmf.items()}
        weight_empirical = Decimal(n) / Decimal(n + self.shrinkage_games) if self.shrinkage_games else Decimal(1)
        weight_global = Decimal(1) - weight_empirical
        support = set(self.global_opportunity_pmf) | set(empirical)
        out = {}
        for k in support:
            p_emp = Decimal(empirical.get(k, 0)) / Decimal(n)
            p_global = self.global_opportunity_pmf.get(k, Decimal(0))
            out[str(k)] = float(weight_empirical * p_emp + weight_global * p_global)
        total = sum(out.values())
        if total <= 0:
            raise ValueError('opportunity fit has no probability mass')
        return {k: v / total for k, v in out.items()}

    def efficiency_counts(self, observations: Iterable[ValidatedObservation]) -> Tuple[int, int]:
        rows = self._conversion_rows(observations)
        successes = sum(int(v.observation.outcome_value) for v in rows)
        opportunities = sum(v.observation.opportunity_count for v in rows)
        failures = opportunities - successes
        if failures < 0:
            raise ValueError('invalid conversion history')
        return successes, failures

    def fit_predictive_pmf(self, observations: Iterable[ValidatedObservation]):
        rows = self._conversion_rows(observations)
        opportunity_pmf = self.fit_opportunity_pmf(rows)
        successes, failures = self.efficiency_counts(rows)
        predictive = mixture_opportunity_pmf(
            opportunity_pmf, successes, failures,
            prior_alpha=self.prior_alpha, prior_beta=self.prior_beta)
        return {
            'mode': 'OFFLINE_VALIDATED_HISTORY_FIT',
            'forecast_status': 'HOLD',
            'wager_status': 'NOT APPROVED',
            'calibration_verified': False,
            'joint_simulation_performed': False,
            'n_observations': len(rows),
            'opportunity_pmf': opportunity_pmf,
            'posterior_alpha': str(self.prior_alpha + successes),
            'posterior_beta': str(self.prior_beta + failures),
            'predictive_pmf': predictive,
            'warning': 'Provider semantics and trusted-source policy configuration remain external obligations.',
        }
