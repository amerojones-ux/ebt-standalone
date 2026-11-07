"""Synthetic tests for correlated combo and dependency-preserving joint MC."""
import unittest

from extensions.correlated_joint_mc import (
    compare_combo_correlated_vs_independent,
    decompose_combo_leg,
    run_final_joint_parlay_mc,
    run_three_scenario_joint_mc,
    simulate_joint_model,
)

HASH="a"*64


def model(rho=.8):
    return {
        "variables":{
            "X":{"0":"0.5","1":"0.5"},
            "Y":{"0":"0.5","1":"0.5"},
        },
        "variable_order":["X","Y"],
        "latent_correlation":[[1,rho],[rho,1]],
        "model_locked_at":"2026-11-07T18:00:00Z",
        "source_evidence_sha256":HASH,
    }


COMBO={
    "leg_id":"XY_2PLUS",
    "terms":{"X":"1","Y":"1"},
    "comparator":"GE",
    "threshold":"2",
}

PARLAY=[
    {"leg_id":"X_1PLUS","terms":{"X":"1"},"comparator":"GE","threshold":"1"},
    {"leg_id":"Y_1PLUS","terms":{"Y":"1"},"comparator":"GE","threshold":"1"},
]


class CorrelatedJointMCTests(unittest.TestCase):
    def test_combo_decomposition_exposes_component_dependence(self):
        out=decompose_combo_leg(model(.8),COMBO)
        self.assertTrue(out["correlation_required"])
        self.assertAlmostEqual(out["max_absolute_latent_correlation"],.8)
        self.assertEqual(len(out["terms"]),2)
        self.assertFalse(out["market_price_inputs_used"])

    def test_positive_correlation_changes_combo_vs_independence(self):
        out=compare_combo_correlated_vs_independent(
            model(.8),COMBO,trials=100000,
            correlated_seed=101,independent_seed=202)
        self.assertGreater(out["correlated_hit_rate"],out["independent_hit_rate"])
        self.assertGreater(out["correlation_effect_on_hit_rate"],.10)
        self.assertFalse(out["calibration_verified"])

    def test_joint_probability_is_direct_frequency_not_product(self):
        out=simulate_joint_model(
            model(.8),PARLAY,trials=100000,seed=303,label="TEST")
        self.assertTrue(out["joint_probability_is_direct_all_hit_frequency"])
        self.assertFalse(out["individual_probabilities_multiplied"])
        product=(
            out["legs"]["X_1PLUS"]["hit_rate"]
            *out["legs"]["Y_1PLUS"]["hit_rate"]
        )
        self.assertGreater(out["joint_probability"],product)
        self.assertEqual(len(out["input_sha256"]),64)
        self.assertEqual(len(out["code_sha256"]),64)

    def test_negative_correlation_reduces_joint_hit_probability(self):
        positive=simulate_joint_model(
            model(.8),PARLAY,trials=100000,seed=401,label="POS")
        negative=simulate_joint_model(
            model(-.8),PARLAY,trials=100000,seed=402,label="NEG")
        self.assertGreater(
            positive["joint_probability"],
            negative["joint_probability"]+.20)

    def test_non_positive_definite_matrix_is_rejected(self):
        bad=model(1)
        with self.assertRaises(ValueError):
            decompose_combo_leg(bad,COMBO)

    def test_joint_mc_requires_100k(self):
        with self.assertRaises(ValueError):
            simulate_joint_model(
                model(.2),PARLAY,trials=99999,seed=1,label="TOO_SMALL")

    def test_market_field_contamination_is_rejected(self):
        bad=model(.2)
        bad["american_odds"]=200
        with self.assertRaises(ValueError):
            simulate_joint_model(
                bad,PARLAY,trials=100000,seed=1,label="BAD")

    def test_three_scenarios_produce_joint_floor(self):
        models={
            "baseline":model(.8),
            "adversarial":model(-.5),
            "scenario":model(0),
        }
        out=run_three_scenario_joint_mc(
            models,PARLAY,trials=100000,
            seeds={"baseline":11,"adversarial":22,"scenario":33})
        self.assertEqual(
            out["scenario_floor_joint_probability"],
            min(out["joint_probability_by_scenario"].values()))
        self.assertTrue(out["final_joint_parlay_mc_still_required"])
        self.assertEqual(
            set(out["dominant_failure_leg_by_scenario"]),
            {"baseline","adversarial","scenario"})

    def test_three_scenarios_require_distinct_seeds(self):
        models={
            "baseline":model(.2),
            "adversarial":model(.1),
            "scenario":model(0),
        }
        with self.assertRaises(ValueError):
            run_three_scenario_joint_mc(
                models,PARLAY,trials=100000,
                seeds={"baseline":1,"adversarial":1,"scenario":2})

    def test_final_joint_mc_is_separate_and_requires_new_seed(self):
        models={
            "baseline":model(.8),
            "adversarial":model(-.5),
            "scenario":model(0),
        }
        three=run_three_scenario_joint_mc(
            models,PARLAY,trials=100000,
            seeds={"baseline":51,"adversarial":52,"scenario":53})
        with self.assertRaises(ValueError):
            run_final_joint_parlay_mc(
                model(.3),PARLAY,three,trials=100000,seed=51)
        final=run_final_joint_parlay_mc(
            model(.3),PARLAY,three,trials=100000,seed=54)
        self.assertEqual(final["mode"],"FINAL_DEPENDENCY_PRESERVING_JOINT_PARLAY_MC")
        self.assertTrue(final["joint_probability_is_direct_all_hit_frequency"])
        self.assertFalse(final["individual_probabilities_multiplied"])
        self.assertEqual(final["wager_status"],"NOT APPROVED")

    def test_failure_clusters_and_dominant_failure_leg_are_recorded(self):
        out=simulate_joint_model(
            model(.2),PARLAY,trials=100000,seed=99,label="FAILURES")
        self.assertIn(out["dominant_failure_leg"],{"X_1PLUS","Y_1PLUS"})
        self.assertTrue(out["top_failure_clusters"])
        self.assertGreater(out["single_miss_rate"],0)


if __name__=="__main__":
    unittest.main()
