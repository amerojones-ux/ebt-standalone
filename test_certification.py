import unittest
from ebt_certification import (CertificationHold, identity_check, availability_check,
                               historical_certification, release_gate)

class CertificationTests(unittest.TestCase):
    def test_identity_requires_corrob(self):
        event = {"event_id":"g", "team_ids":["a","b"]}
        player = {"player_id":"p","event_id":"g","team_id":"a","identity_corrob":True}
        self.assertTrue(identity_check(event, player))
        for change in ({"identity_corrob":False},{"team_id":"c"},{"event_id":"other"}):
            with self.subTest(change=change), self.assertRaises(CertificationHold):
                identity_check(event, {**player, **change})

    def test_availability_freshness_and_cutoff(self):
        r = {"official_verified":True,"status":"available",
             "published_at":"2026-10-28T12:00:00Z",
             "retrieved_at":"2026-10-28T12:01:00Z"}
        self.assertTrue(availability_check(r, cutoff="2026-10-28T12:05:00Z",max_age_seconds=600))
        for change in ({"official_verified":False},{"status":"questionable"},
                       {"published_at":"2026-10-27T12:00:00Z"},
                       {"retrieved_at":"2026-10-28T12:06:00Z"}):
            with self.subTest(change=change), self.assertRaises(CertificationHold):
                availability_check({**r, **change},cutoff="2026-10-28T12:05:00Z",max_age_seconds=600)

    def test_historical_temporal_certification(self):
        r = {"event_id":"g","player_id":"p","team_id":"a",
             "market_definition":"points >= 10","threshold":"10",
             "source_capture_ids":["sha256:fixture"],"model_version":"test",
             "outcome_source":"official","feature_asof":"2026-10-28T09:00:00Z",
             "prediction_created_at":"2026-10-28T10:00:00Z",
             "scheduled_start":"2026-10-28T23:00:00Z",
             "outcome_final_at":"2026-10-29T02:00:00Z",
             "certification_status":"independently_reviewed","outcome_verified":True}
        self.assertTrue(historical_certification(r))
        for change in ({"certification_status":"claimed"},
                       {"outcome_verified":False},
                       {"feature_asof":"2026-10-28T23:01:00Z"},
                       {"source_capture_ids":[]}):
            with self.subTest(change=change), self.assertRaises(CertificationHold):
                historical_certification({**r, **change})

    def test_release_never_automatically_approves(self):
        self.assertEqual(release_gate()["status"],"HOLD")
        self.assertEqual(release_gate(access_authorized=True,history_certified=True,
            calibration_approved=True,source_verified=True,operational_signoff=True)["status"],"REVIEW_REQUIRED")
        self.assertFalse(release_gate(access_authorized=True,history_certified=True,
            calibration_approved=True,source_verified=True,operational_signoff=True)["forecast_approved"])

if __name__ == "__main__":
    unittest.main()
