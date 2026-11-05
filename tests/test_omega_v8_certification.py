import unittest
from omega_v8.certification import CertificationEvidence,certify,lock_forecast,verify_locked_forecast

def evidence(**changes):
    values=dict(probability="0.91",lower_bound="0.83",central_cushion="1.5",adverse_cushion=".5",
                source_verified=True,roster_verified=True,role_verified=True,
                calibrated_out_of_sample=True,scenario_verified=True,threshold_locked=True,injury_resolved=True)
    values.update(changes)
    return CertificationEvidence(**values)

class CertificationTests(unittest.TestCase):
    def test_qualified_research_never_approves_wager(self):
        result=certify(evidence())
        self.assertEqual(result["status"],"CERTIFIED_RESEARCH")
        self.assertEqual(result["wager_status"],"NOT_APPROVED")
    def test_missing_evidence_holds(self):
        self.assertEqual(certify(evidence(source_verified=False))["status"],"HOLD")
    def test_boundary(self):
        self.assertEqual(certify(evidence(probability="0.87",lower_bound="0.80"))["status"],"CERTIFIED_RESEARCH")
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):certify(evidence(probability="NaN"))
    def test_locked_forecast_tampering(self):
        forecast={"forecast_id":"f1","issued_at":"2026-11-05T10:00:00-06:00",
                  "event_at":"2026-11-05T19:00:00-06:00","player":"Synthetic Player",
                  "market":"REB","threshold":8,"model_version":"omega-v8-research","probability":"0.89"}
        locked=lock_forecast(forecast)
        self.assertTrue(verify_locked_forecast(locked))
        forecast["threshold"]=9
        self.assertFalse(verify_locked_forecast(locked))
    def test_post_start_rejected(self):
        forecast={"forecast_id":"f1","issued_at":"2026-11-05T20:00:00Z",
                  "event_at":"2026-11-05T19:00:00Z","player":"Synthetic Player",
                  "market":"REB","threshold":8,"model_version":"omega-v8-research","probability":"0.89"}
        with self.assertRaises(ValueError):lock_forecast(forecast)

if __name__=="__main__":unittest.main()
