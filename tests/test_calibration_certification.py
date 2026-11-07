"""End-to-end synthetic tests for calibration certification review."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from extensions.calibration_certification import (
    assess_calibration_certification_review,
    candidate_calibration_uncertainty_diagnostic,
    verify_calibration_review_receipt,
)

SCOPE={
    "competition":"NBA",
    "market":"PLAYER_POINTS",
    "threshold_type":"ALTERNATE",
    "model_version":"M-1",
}
FIT_AT="2026-10-01T00:00:00Z"
ASSESSED_AT="2026-11-01T00:00:00Z"

RESEARCH_POLICY={
    "version":"1.0",
    "min_training_rows":20,
    "min_training_events":20,
    "min_validation_rows":10,
    "min_validation_events":10,
}

ACCEPTANCE_POLICY={
    "policy_id":"CAL-NBA-POINTS-V1",
    "declared_at":"2026-08-01T00:00:00Z",
    "max_validation_brier":"0.20",
    "max_validation_expected_calibration_error":"0.05",
    "max_validation_max_calibration_gap":"0.10",
    "minimum_calibration_block_count":20,
    "require_calibrated_brier_not_worse_than_raw":True,
}


def row(event_id,p,hit,issued,event,outcome):
    return {
        "competition":SCOPE["competition"],
        "market":SCOPE["market"],
        "threshold_type":SCOPE["threshold_type"],
        "model_version":SCOPE["model_version"],
        "event_id":event_id,
        "forecast_id":"F-"+event_id,
        "p":str(p),
        "result":"HIT" if hit else "MISS",
        "certified":True,
        "training_end":(issued-timedelta(days=1)).isoformat(),
        "issued_at":issued.isoformat(),
        "event_start":event.isoformat(),
        "outcome_available_at":outcome.isoformat(),
    }


def cohorts():
    training=[]
    base=datetime(2026,8,10,tzinfo=timezone.utc)
    for i in range(20):
        issued=base+timedelta(days=i)
        training.append(row(
            f"TLOW{i:02d}",".2",i<4,
            issued,issued+timedelta(hours=1),issued+timedelta(hours=3)))
    base=datetime(2026,9,1,tzinfo=timezone.utc)
    for i in range(20):
        issued=base+timedelta(days=i)
        training.append(row(
            f"THIGH{i:02d}",".8",i<16,
            issued,issued+timedelta(hours=1),issued+timedelta(hours=3)))

    validation=[]
    base=datetime(2026,10,5,tzinfo=timezone.utc)
    for i in range(10):
        issued=base+timedelta(days=i)
        validation.append(row(
            f"VLOW{i:02d}",".2",i<2,
            issued,issued+timedelta(hours=1),issued+timedelta(hours=3)))
    base=datetime(2026,10,16,tzinfo=timezone.utc)
    for i in range(10):
        issued=base+timedelta(days=i)
        validation.append(row(
            f"VHIGH{i:02d}",".8",i<8,
            issued,issued+timedelta(hours=1),issued+timedelta(hours=3)))
    return training,validation


def review(acceptance=None,research=None,training=None,validation=None):
    t,v=cohorts()
    return assess_calibration_certification_review(
        t if training is None else training,
        v if validation is None else validation,
        scope=SCOPE,
        fit_at=FIT_AT,
        assessed_at=ASSESSED_AT,
        research_policy=RESEARCH_POLICY if research is None else research,
        acceptance_policy=ACCEPTANCE_POLICY if acceptance is None else acceptance,
    )


def high_confidence_cohorts():
    training=[]
    base=datetime(2026,6,1,tzinfo=timezone.utc)
    for i in range(100):
        issued=base+timedelta(hours=4*i)
        training.append(row(
            f"HIGH{i:03d}",".95",i<95,
            issued,issued+timedelta(minutes=30),issued+timedelta(hours=2)))
    base=datetime(2026,7,1,tzinfo=timezone.utc)
    for i in range(100):
        issued=base+timedelta(hours=4*i)
        training.append(row(
            f"LOW{i:03d}",".2",i<20,
            issued,issued+timedelta(minutes=30),issued+timedelta(hours=2)))
    validation=[]
    base=datetime(2026,10,2,tzinfo=timezone.utc)
    for i in range(20):
        issued=base+timedelta(hours=8*i)
        validation.append(row(
            f"VH{i:03d}",".95",i<19,
            issued,issued+timedelta(minutes=30),issued+timedelta(hours=2)))
    base=datetime(2026,10,10,tzinfo=timezone.utc)
    for i in range(20):
        issued=base+timedelta(hours=8*i)
        validation.append(row(
            f"VL{i:03d}",".2",i<4,
            issued,issued+timedelta(minutes=30),issued+timedelta(hours=2)))
    return training,validation


class CalibrationCertificationTests(unittest.TestCase):
    def test_good_temporal_calibration_package_is_review_eligible_only(self):
        out=review()
        self.assertEqual(
            out["status"],"CALIBRATION_CERTIFICATION_REVIEW_ELIGIBLE")
        self.assertTrue(out["certification_review_eligible"])
        self.assertFalse(out["calibration_verified"])
        self.assertFalse(out["calibration_certificate_issued"])
        self.assertFalse(out["model_promotion_applied"])
        self.assertTrue(out["requires_human_acceptance"])
        self.assertEqual(out["reasons"],[])
        self.assertEqual(out["minimum_fitted_block_count"],20)
        self.assertEqual(
            out["validation_reliability_metrics"]["expected_calibration_error"],
            0.0,
        )
        self.assertEqual(
            out["validation_reliability_metrics"]["max_calibration_gap"],
            0.0,
        )

    def test_acceptance_policy_must_be_declared_before_fit(self):
        policy=dict(ACCEPTANCE_POLICY)
        policy["declared_at"]=FIT_AT
        out=review(acceptance=policy)
        self.assertEqual(out["status"],"HOLD")
        self.assertIn(
            "ACCEPTANCE_POLICY_NOT_PREDECLARED_BEFORE_FIT",out["reasons"])

    def test_validation_brier_policy_is_enforced(self):
        policy=dict(ACCEPTANCE_POLICY)
        policy["max_validation_brier"]="0.10"
        out=review(acceptance=policy)
        self.assertIn("VALIDATION_BRIER_EXCEEDS_POLICY",out["reasons"])

    def test_validation_ece_policy_is_enforced(self):
        t,v=cohorts()
        for i,r in enumerate(v):
            r["result"]="MISS" if i<10 else "HIT"
        policy=dict(ACCEPTANCE_POLICY)
        policy["max_validation_brier"]="1"
        policy["max_validation_expected_calibration_error"]="0.01"
        policy["max_validation_max_calibration_gap"]="1"
        policy["require_calibrated_brier_not_worse_than_raw"]=False
        out=review(acceptance=policy,training=t,validation=v)
        self.assertIn("VALIDATION_ECE_EXCEEDS_POLICY",out["reasons"])

    def test_validation_max_gap_policy_is_enforced(self):
        t,v=cohorts()
        for i,r in enumerate(v):
            if r["p"]==".2":
                r["result"]="MISS"
        policy=dict(ACCEPTANCE_POLICY)
        policy["max_validation_brier"]="1"
        policy["max_validation_expected_calibration_error"]="1"
        policy["max_validation_max_calibration_gap"]="0.05"
        policy["require_calibrated_brier_not_worse_than_raw"]=False
        out=review(acceptance=policy,training=t,validation=v)
        self.assertIn("VALIDATION_MAX_GAP_EXCEEDS_POLICY",out["reasons"])

    def test_minimum_calibration_block_count_is_policy_driven(self):
        policy=dict(ACCEPTANCE_POLICY)
        policy["minimum_calibration_block_count"]=21
        out=review(acceptance=policy)
        self.assertIn("CALIBRATION_BLOCK_SAMPLE_BELOW_POLICY",out["reasons"])

    def test_underlying_temporal_assessment_hold_propagates(self):
        t,v=cohorts()
        research=dict(RESEARCH_POLICY)
        research["min_validation_rows"]=25
        out=review(research=research,training=t,validation=v)
        self.assertIn("UNDERLYING_CALIBRATION_ASSESSMENT_HOLD",out["reasons"])
        self.assertFalse(out["certification_review_eligible"])

    def test_training_and_validation_are_immutably_hashed_separately(self):
        out=review()
        self.assertEqual(len(out["training_sha256"]),64)
        self.assertEqual(len(out["validation_sha256"]),64)
        self.assertNotEqual(out["training_sha256"],out["validation_sha256"])
        self.assertEqual(len(out["calibration_map_sha256"]),64)

    def test_review_receipt_detects_tampering_and_cannot_self_certify(self):
        out=review()
        self.assertTrue(verify_calibration_review_receipt(out))
        tampered=copy.deepcopy(out)
        tampered["minimum_fitted_block_count"]=999
        with self.assertRaises(ValueError):
            verify_calibration_review_receipt(tampered)
        tampered=copy.deepcopy(out)
        tampered["calibration_verified"]=True
        with self.assertRaises(ValueError):
            verify_calibration_review_receipt(tampered)

    def test_candidate_diagnostic_requires_at_least_100k_trials(self):
        out=review()
        with self.assertRaises(ValueError):
            candidate_calibration_uncertainty_diagnostic(
                out,".8",trials=99999,seed=7)

    def test_candidate_diagnostic_exposes_modeled_87_80_gates_without_certifying(self):
        training,validation=high_confidence_cohorts()
        research={
            "version":"1.0",
            "min_training_rows":100,
            "min_training_events":100,
            "min_validation_rows":20,
            "min_validation_events":20,
        }
        acceptance={
            "policy_id":"CAL-HIGH-V1",
            "declared_at":"2026-05-01T00:00:00Z",
            "max_validation_brier":"0.20",
            "max_validation_expected_calibration_error":"0.10",
            "max_validation_max_calibration_gap":"0.10",
            "minimum_calibration_block_count":50,
            "require_calibrated_brier_not_worse_than_raw":True,
        }
        receipt=review(
            acceptance=acceptance,research=research,
            training=training,validation=validation)
        self.assertTrue(receipt["certification_review_eligible"])
        diag=candidate_calibration_uncertainty_diagnostic(
            receipt,".95",trials=100000,seed=123)
        self.assertGreaterEqual(diag["isotonic_calibrated_probability"],.87)
        self.assertGreaterEqual(diag["jeffreys_probability_p05"],.80)
        self.assertTrue(
            diag["black_diamond_probability_thresholds_modeled"]
            ["both_modeled_probability_gates"])
        self.assertFalse(diag["calibration_verified"])
        self.assertEqual(diag["wager_status"],"NOT APPROVED")

    def test_candidate_diagnostic_rejects_ineligible_review(self):
        policy=dict(ACCEPTANCE_POLICY)
        policy["max_validation_brier"]="0.01"
        out=review(acceptance=policy)
        self.assertFalse(out["certification_review_eligible"])
        with self.assertRaises(ValueError):
            candidate_calibration_uncertainty_diagnostic(
                out,".8",trials=100000,seed=7)


if __name__=="__main__":
    unittest.main()
