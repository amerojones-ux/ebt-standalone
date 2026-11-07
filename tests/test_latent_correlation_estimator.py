"""Synthetic tests for leakage-safe latent correlation estimation."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from extensions.latent_correlation_estimator import (
    build_joint_model_from_correlation_estimate,
    estimate_latent_correlation,
)
from extensions.correlated_joint_mc import decompose_combo_leg

CUTOFF="2026-11-07T18:00:00Z"
VARIABLES=["X","Y"]
POLICY={
    "min_complete_events":20,
    "recent_window_events":10,
    "shrinkage_to_identity":"0.1",
    "max_allowed_abs_drift":"0.2",
    "max_pair_ci_width":"0.2",
}


def history(n=30,mode="positive"):
    start=datetime(2026,9,1,tzinfo=timezone.utc)
    rows=[]
    for i in range(n):
        event=f"E{i:03d}"
        event_time=start+timedelta(days=i)
        for var in VARIABLES:
            x=float(i)
            if var=="X":
                value=x
            elif mode=="positive":
                value=x
            elif mode=="negative":
                value=-x
            elif mode=="drift":
                value=x if i<n-10 else -x
            elif mode=="weak":
                value=float((i*7)%max(n,2))
            elif mode=="constant":
                value=1.0
            else:
                raise ValueError("unknown mode")
            rows.append({
                "event_id":event,
                "variable_id":var,
                "value":str(value),
                "event_time":event_time.isoformat(),
                "outcome_available_at":(event_time+timedelta(hours=3)).isoformat(),
                "source_record_sha256":hashlib.sha256(
                    f"{event}|{var}|{value}".encode()).hexdigest(),
            })
    return rows


class LatentCorrelationEstimatorTests(unittest.TestCase):
    def test_stable_positive_rank_dependence_produces_shrunk_matrix(self):
        out=estimate_latent_correlation(
            history(),variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)
        self.assertEqual(out["status"],"RESEARCH_INPUT")
        self.assertAlmostEqual(out["raw_normal_score_correlation"][0][1],1.0)
        self.assertAlmostEqual(out["latent_correlation"][0][1],.9)
        self.assertTrue(out["positive_definite"])
        self.assertEqual(out["reasons"],[])
        self.assertFalse(out["market_inputs_used"])

    def test_stable_negative_dependence_is_preserved_with_shrinkage(self):
        out=estimate_latent_correlation(
            history(mode="negative"),variable_ids=VARIABLES,
            forecast_cutoff=CUTOFF,policy=POLICY)
        self.assertAlmostEqual(out["latent_correlation"][0][1],-.9)
        self.assertEqual(out["status"],"RESEARCH_INPUT")

    def test_complete_case_coverage_is_explicit(self):
        rows=history()
        rows=[
            row for row in rows
            if not (row["event_id"]=="E005" and row["variable_id"]=="Y")
        ]
        out=estimate_latent_correlation(
            rows,variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)
        self.assertEqual(out["historical_event_count"],30)
        self.assertEqual(out["complete_event_count"],29)
        self.assertAlmostEqual(out["complete_case_coverage"],29/30)

    def test_temporal_correlation_reversal_forces_hold(self):
        out=estimate_latent_correlation(
            history(n=40,mode="drift"),variable_ids=VARIABLES,
            forecast_cutoff=CUTOFF,policy=POLICY)
        self.assertEqual(out["status"],"HOLD")
        self.assertGreater(out["max_absolute_temporal_drift"],1.5)
        self.assertIn("CORRELATION_DRIFT_EXCEEDS_POLICY",out["reasons"])

    def test_wide_pair_uncertainty_forces_hold(self):
        policy=dict(POLICY)
        policy["max_pair_ci_width"]="0.2"
        out=estimate_latent_correlation(
            history(n=20,mode="weak"),variable_ids=VARIABLES,
            forecast_cutoff=CUTOFF,policy=policy)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn("PAIRWISE_CORRELATION_UNCERTAINTY_TOO_WIDE",out["reasons"])

    def test_insufficient_complete_sample_holds_without_matrix_claim(self):
        out=estimate_latent_correlation(
            history(n=10),variable_ids=VARIABLES,
            forecast_cutoff=CUTOFF,policy=POLICY)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn("INSUFFICIENT_COMPLETE_EVENTS",out["reasons"])
        self.assertIn("INSUFFICIENT_DRIFT_WINDOWS",out["reasons"])
        self.assertNotIn("latent_correlation",out)

    def test_outcome_at_forecast_cutoff_is_rejected_strictly(self):
        rows=history()
        rows[0]["outcome_available_at"]=CUTOFF
        with self.assertRaises(ValueError):
            estimate_latent_correlation(
                rows,variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)

    def test_duplicate_event_variable_is_rejected(self):
        rows=history()
        rows.append(dict(rows[0]))
        with self.assertRaises(ValueError):
            estimate_latent_correlation(
                rows,variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)

    def test_event_time_mismatch_within_event_is_rejected(self):
        rows=history()
        for row in rows:
            if row["event_id"]=="E000" and row["variable_id"]=="Y":
                row["event_time"]="2026-09-01T01:00:00+00:00"
        with self.assertRaises(ValueError):
            estimate_latent_correlation(
                rows,variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)

    def test_zero_variance_variable_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_latent_correlation(
                history(mode="constant"),variable_ids=VARIABLES,
                forecast_cutoff=CUTOFF,policy=POLICY)

    def test_market_field_contamination_is_rejected(self):
        rows=history()
        rows[0]["sportsbook_price"]=-110
        with self.assertRaises(ValueError):
            estimate_latent_correlation(
                rows,variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)

    def test_research_eligible_matrix_builds_exact_joint_model_schema(self):
        receipt=estimate_latent_correlation(
            history(),variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)
        model=build_joint_model_from_correlation_estimate(
            {
                "X":{"0":"0.5","1":"0.5"},
                "Y":{"0":"0.5","1":"0.5"},
            },
            receipt,model_locked_at="2026-11-07T18:01:00Z")
        self.assertEqual(set(model),{
            "variables","variable_order","latent_correlation",
            "model_locked_at","source_evidence_sha256",
        })
        self.assertEqual(model["source_evidence_sha256"],receipt["matrix_sha256"])
        self.assertEqual(model["variable_order"],VARIABLES)
        combo=decompose_combo_leg(
            model,{
                "leg_id":"XY","terms":{"X":"1","Y":"1"},
                "comparator":"GE","threshold":"1",
            })
        self.assertAlmostEqual(combo["max_absolute_latent_correlation"],.9)

    def test_hold_matrix_cannot_feed_joint_model(self):
        receipt=estimate_latent_correlation(
            history(n=10),variable_ids=VARIABLES,forecast_cutoff=CUTOFF,policy=POLICY)
        with self.assertRaises(ValueError):
            build_joint_model_from_correlation_estimate(
                {"X":{"0":"1"},"Y":{"0":"1"}},
                receipt,model_locked_at="2026-11-07T18:01:00Z")


if __name__=="__main__":
    unittest.main()
