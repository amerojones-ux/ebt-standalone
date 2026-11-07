"""Synthetic tests for Bayesian rare-event distributions."""
import unittest

from extensions.bayesian_rare_events import (
    fit_binary_rare_event_posterior,
    fit_competing_event_posterior,
    run_three_competing_event_scenarios,
    simulate_binary_posterior_uncertainty,
    simulate_competing_posterior_uncertainty,
)

CUTOFF="2026-11-07T18:00:00Z"


def competing_rows(a=2,b=1,other=7):
    return [
        {
            "candidate_id":"A","prior_alpha":"1","historical_first_events":a,
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
        {
            "candidate_id":"B","prior_alpha":"1","historical_first_events":b,
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
        {
            "candidate_id":"OTHER","prior_alpha":"1","historical_first_events":other,
            "evidence_available_at":"2026-11-07T17:00:00Z",
        },
    ]


def posterior(a=2,b=1,other=7):
    return fit_competing_event_posterior(
        competing_rows(a,b,other),cutoff=CUTOFF,
        residual_category_id="OTHER",candidate_universe_complete=True)


class BayesianRareEventTests(unittest.TestCase):
    def test_competing_posterior_preserves_complete_probability_mass(self):
        out=posterior()
        probs=out["posterior_mean_probability"]
        self.assertAlmostEqual(sum(probs.values()),1.0)
        self.assertEqual(out["historical_event_count"],10)
        self.assertGreater(probs["OTHER"],probs["A"])
        self.assertFalse(out["price_inputs_used"])
        self.assertFalse(out["calibration_verified"])

    def test_residual_category_is_required(self):
        with self.assertRaises(ValueError):
            fit_competing_event_posterior(
                competing_rows(),cutoff=CUTOFF,
                residual_category_id="MISSING",candidate_universe_complete=True)

    def test_incomplete_candidate_universe_is_rejected(self):
        with self.assertRaises(ValueError):
            fit_competing_event_posterior(
                competing_rows(),cutoff=CUTOFF,
                residual_category_id="OTHER",candidate_universe_complete=False)

    def test_post_cutoff_competing_evidence_is_rejected(self):
        rows=competing_rows()
        rows[0]["evidence_available_at"]="2026-11-07T18:00:01Z"
        with self.assertRaises(ValueError):
            fit_competing_event_posterior(
                rows,cutoff=CUTOFF,
                residual_category_id="OTHER",candidate_universe_complete=True)

    def test_sportsbook_field_is_rejected_from_competing_fit(self):
        rows=competing_rows()
        rows[0]["american_odds"]=500
        with self.assertRaises(ValueError):
            fit_competing_event_posterior(
                rows,cutoff=CUTOFF,
                residual_category_id="OTHER",candidate_universe_complete=True)

    def test_competing_uncertainty_requires_100k_and_has_ordered_interval(self):
        p=posterior()
        with self.assertRaises(ValueError):
            simulate_competing_posterior_uncertainty(p,trials=99999,seed=7)
        out=simulate_competing_posterior_uncertainty(p,trials=100000,seed=7)
        a=out["candidates"]["A"]
        self.assertLess(a["probability_p05"],a["probability_p50"])
        self.assertLess(a["probability_p50"],a["probability_p95"])
        rank_mass=sum(x["posterior_rank1_probability"] for x in out["candidates"].values())
        self.assertAlmostEqual(rank_mass,1.0,places=8)
        self.assertFalse(out["game_outcome_monte_carlo"])

    def test_three_scenarios_expose_probability_floor(self):
        posts={
            "baseline":posterior(3,2,5),
            "adversarial":posterior(1,2,7),
            "scenario":posterior(2,1,7),
        }
        out=run_three_competing_event_scenarios(
            posts,trials=100000,seeds={"baseline":11,"adversarial":22,"scenario":33})
        a=out["candidates"]["A"]
        self.assertEqual(
            a["mean_probability_floor"],
            min(a["scenario_mean_probabilities"].values()))
        self.assertLessEqual(a["posterior_p05_floor"],a["mean_probability_floor"])
        self.assertEqual(out["trials_each"],100000)
        self.assertFalse(out["calibration_verified"])

    def test_three_scenarios_require_distinct_seeds(self):
        posts={
            "baseline":posterior(),
            "adversarial":posterior(),
            "scenario":posterior(),
        }
        with self.assertRaises(ValueError):
            run_three_competing_event_scenarios(
                posts,trials=100000,
                seeds={"baseline":1,"adversarial":1,"scenario":2})

    def test_binary_posterior_preserves_exact_event_definition(self):
        out=fit_binary_rare_event_posterior(
            event_definition="score_3_plus_first_3_minutes",
            prior_alpha="1",prior_beta="1",successes=2,failures=8,
            evidence_available_at="2026-11-07T17:00:00Z",cutoff=CUTOFF)
        self.assertEqual(out["event_definition"],"score_3_plus_first_3_minutes")
        self.assertAlmostEqual(out["posterior_mean_probability"],0.25)
        self.assertFalse(out["price_inputs_used"])

    def test_binary_uncertainty_requires_100k(self):
        p=fit_binary_rare_event_posterior(
            event_definition="early_event",
            prior_alpha="1",prior_beta="1",successes=2,failures=8,
            evidence_available_at="2026-11-07T17:00:00Z",cutoff=CUTOFF)
        with self.assertRaises(ValueError):
            simulate_binary_posterior_uncertainty(p,trials=99999,seed=5)
        out=simulate_binary_posterior_uncertainty(p,trials=100000,seed=5)
        self.assertLess(out["probability_p05"],out["probability_p50"])
        self.assertLess(out["probability_p50"],out["probability_p95"])
        self.assertFalse(out["game_outcome_monte_carlo"])

    def test_binary_post_cutoff_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            fit_binary_rare_event_posterior(
                event_definition="early_event",
                prior_alpha="1",prior_beta="1",successes=1,failures=9,
                evidence_available_at="2026-11-07T18:00:01Z",cutoff=CUTOFF)


if __name__=="__main__":
    unittest.main()
