"""Synthetic tests for V7 learning-change governance."""
import copy
import unittest

from extensions.learning_change_governance import (
    assess_learning_change_review,
    verify_learning_review_receipt,
)

A="a"*64
B="b"*64
C="c"*64
D="d"*64
E="e"*64
F="f"*64
G="1"*64
H="2"*64


def window(
    window_id,start,end,*,brier_reference="0.18",brier_current="0.205",
    gap="0.03",sha=A,
):
    return {
        "window_id":window_id,
        "start":start,
        "end":end,
        "settled_count":25,
        "brier_reference":brier_reference,
        "brier_current":brier_current,
        "calibration_gap_current":gap,
        "evidence_sha256":sha,
    }


def request():
    return {
        "request_id":"LR-001",
        "market_key":"NBA_PLAYER_POINTS_OVER",
        "settled_market_count":35,
        "settled_model_count":60,
        "settled_market_sample_sha256":G,
        "settled_model_sample_sha256":H,
        "review_cutoff":"2026-11-07T18:00:00Z",
        "degraded_windows":[
            window(
                "W1","2026-09-01T00:00:00Z","2026-09-15T00:00:00Z",
                brier_reference="0.18",brier_current="0.205",gap="0.03",sha=A,
            ),
            window(
                "W2","2026-09-15T00:00:00Z","2026-10-01T00:00:00Z",
                brier_reference="0.19",brier_current="0.195",gap="0.06",sha=B,
            ),
        ],
        "root_cause":{
            "completed":True,
            "completed_at":"2026-10-10T00:00:00Z",
            "finding":"Role-state sensitivity is underweighted in verified cohorts.",
            "identifiability":"PRE_GAME_IDENTIFIABLE",
            "isolated_outcome_only":False,
            "evidence_items":[
                {"kind":"LOCKED_FORECAST_LEDGER","sha256":C},
                {"kind":"CALIBRATION_REPORT","sha256":D},
            ],
        },
        "backtest":{
            "completed":True,
            "completed_at":"2026-11-01T00:00:00Z",
            "baseline_version":"M-1",
            "candidate_version":"M-2",
            "heldout_events":40,
            "heldout_brier_baseline":"0.21",
            "heldout_brier_candidate":"0.19",
            "heldout_calibration_gap_baseline":"0.07",
            "heldout_calibration_gap_candidate":"0.04",
            "evidence_sha256":E,
        },
        "versioning":{
            "current_version":"M-1",
            "proposed_version":"M-2",
            "rollback_version":"M-1",
            "rollback_path":"releases/M-1/rollback.json",
        },
        "proposed_change_summary":"Increase role-state sensitivity after reviewed cohort failure.",
    }


class LearningChangeGovernanceTests(unittest.TestCase):
    def test_exact_v7_gates_can_make_request_review_eligible_only(self):
        out=assess_learning_change_review(request())
        self.assertEqual(out["status"],"LEARNING_CHANGE_REVIEW_ELIGIBLE")
        self.assertTrue(out["eligible_for_model_change_review"])
        self.assertEqual(out["reasons"],[])
        self.assertFalse(out["weight_change_applied"])
        self.assertFalse(out["threshold_change_applied"])
        self.assertFalse(out["model_promotion_applied"])
        self.assertTrue(out["requires_human_acceptance"])
        self.assertEqual(
            out["v7_thresholds"]["minimum_settled_per_market"],30)
        self.assertEqual(
            out["v7_thresholds"]["minimum_settled_per_model"],50)

    def test_brier_worsening_exactly_point_02_qualifies(self):
        row=request()
        row["degraded_windows"][0]["brier_current"]="0.20"
        row["degraded_windows"][0]["brier_reference"]="0.18"
        out=assess_learning_change_review(row)
        w1=next(x for x in out["degraded_windows"] if x["window_id"]=="W1")
        self.assertTrue(w1["qualifies_as_degraded"])
        self.assertEqual(w1["brier_worsening"],"0.02")

    def test_calibration_gap_exactly_point_05_qualifies(self):
        row=request()
        row["degraded_windows"][1]["brier_current"]="0.19"
        row["degraded_windows"][1]["brier_reference"]="0.19"
        row["degraded_windows"][1]["calibration_gap_current"]="0.05"
        out=assess_learning_change_review(row)
        w2=next(x for x in out["degraded_windows"] if x["window_id"]=="W2")
        self.assertTrue(w2["qualifies_as_degraded"])

    def test_insufficient_market_sample_holds(self):
        row=request()
        row["settled_market_count"]=29
        out=assess_learning_change_review(row)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn("INSUFFICIENT_SETTLED_MARKET_SAMPLE",out["reasons"])

    def test_insufficient_model_sample_holds(self):
        row=request()
        row["settled_model_count"]=49
        out=assess_learning_change_review(row)
        self.assertIn("INSUFFICIENT_SETTLED_MODEL_SAMPLE",out["reasons"])

    def test_fewer_than_two_windows_is_schema_error(self):
        row=request()
        row["degraded_windows"]=row["degraded_windows"][:1]
        with self.assertRaises(ValueError):
            assess_learning_change_review(row)

    def test_nondegraded_window_holds_even_if_other_window_degraded(self):
        row=request()
        row["degraded_windows"][1]["brier_current"]="0.191"
        row["degraded_windows"][1]["brier_reference"]="0.19"
        row["degraded_windows"][1]["calibration_gap_current"]="0.049"
        out=assess_learning_change_review(row)
        self.assertIn("FEWER_THAN_TWO_QUALIFYING_DEGRADED_WINDOWS",out["reasons"])
        self.assertIn("WINDOW_NOT_DEGRADED:W2",out["reasons"])

    def test_overlapping_degraded_windows_are_rejected(self):
        row=request()
        row["degraded_windows"][1]["start"]="2026-09-14T00:00:00Z"
        with self.assertRaises(ValueError):
            assess_learning_change_review(row)

    def test_window_must_end_before_review_cutoff(self):
        row=request()
        row["degraded_windows"][1]["end"]="2026-11-07T18:00:00Z"
        with self.assertRaises(ValueError):
            assess_learning_change_review(row)

    def test_screenshot_ticket_only_root_cause_evidence_cannot_qualify(self):
        row=request()
        row["root_cause"]["evidence_items"]=[
            {"kind":"SCREENSHOT","sha256":C},
            {"kind":"TICKET","sha256":D},
        ]
        out=assess_learning_change_review(row)
        self.assertIn("ROOT_CAUSE_LACKS_NONISOLATED_EVIDENCE",out["reasons"])

    def test_isolated_outcome_flag_holds(self):
        row=request()
        row["root_cause"]["isolated_outcome_only"]=True
        out=assess_learning_change_review(row)
        self.assertIn("ROOT_CAUSE_ISOLATED_OUTCOME_ONLY",out["reasons"])

    def test_postgame_only_root_cause_cannot_be_production_learning_evidence(self):
        row=request()
        row["root_cause"]["identifiability"]="POSTGAME_ONLY"
        out=assess_learning_change_review(row)
        self.assertIn(
            "ROOT_CAUSE_POSTGAME_ONLY_NOT_PRODUCTION_LEARNING_EVIDENCE",
            out["reasons"],
        )

    def test_incomplete_root_cause_review_holds(self):
        row=request()
        row["root_cause"]["completed"]=False
        out=assess_learning_change_review(row)
        self.assertIn("ROOT_CAUSE_REVIEW_INCOMPLETE",out["reasons"])

    def test_backtest_is_required_but_no_unwritten_improvement_threshold_added(self):
        row=request()
        row["backtest"]["heldout_brier_candidate"]="0.22"
        row["backtest"]["heldout_calibration_gap_candidate"]="0.08"
        out=assess_learning_change_review(row)
        self.assertTrue(out["eligible_for_model_change_review"])
        self.assertEqual(
            out["backtest"]["brier_delta_candidate_minus_baseline"],"0.01")
        self.assertEqual(
            out["backtest"]["calibration_gap_delta_candidate_minus_baseline"],
            "0.01",
        )
        self.assertFalse(out["model_promotion_applied"])

    def test_incomplete_backtest_holds(self):
        row=request()
        row["backtest"]["completed"]=False
        out=assess_learning_change_review(row)
        self.assertIn("HELDOUT_BACKTEST_INCOMPLETE",out["reasons"])

    def test_proposed_version_must_be_new(self):
        row=request()
        row["versioning"]["proposed_version"]="M-1"
        row["backtest"]["candidate_version"]="M-1"
        out=assess_learning_change_review(row)
        self.assertIn("PROPOSED_VERSION_NOT_NEW",out["reasons"])

    def test_rollback_must_point_to_current_version(self):
        row=request()
        row["versioning"]["rollback_version"]="M-0"
        out=assess_learning_change_review(row)
        self.assertIn(
            "ROLLBACK_VERSION_MUST_MATCH_CURRENT_VERSION",out["reasons"])

    def test_backtest_versions_must_match_versioning(self):
        row=request()
        row["backtest"]["baseline_version"]="M-0"
        row["backtest"]["candidate_version"]="M-3"
        out=assess_learning_change_review(row)
        self.assertIn("BACKTEST_BASELINE_VERSION_MISMATCH",out["reasons"])
        self.assertIn("BACKTEST_CANDIDATE_VERSION_MISMATCH",out["reasons"])

    def test_sample_count_claims_require_valid_immutable_hashes(self):
        row=request()
        row["settled_market_sample_sha256"]="not-a-hash"
        with self.assertRaises(ValueError):
            assess_learning_change_review(row)

    def test_receipt_verification_detects_tampering(self):
        out=assess_learning_change_review(request())
        self.assertTrue(verify_learning_review_receipt(out))
        tampered=copy.deepcopy(out)
        tampered["settled_market_count"]=999
        with self.assertRaises(ValueError):
            verify_learning_review_receipt(tampered)

    def test_receipt_cannot_claim_weight_application(self):
        out=assess_learning_change_review(request())
        tampered=copy.deepcopy(out)
        tampered["weight_change_applied"]=True
        with self.assertRaises(ValueError):
            verify_learning_review_receipt(tampered)


if __name__=="__main__":
    unittest.main()
