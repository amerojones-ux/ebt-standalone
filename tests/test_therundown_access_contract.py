import unittest
from therundown_access_contract import (
    classify_plan,
    validate_plan,
    is_public_reference_path,
    can_use_for_live_model_evidence,
    can_authorize_authenticated_request,
)

PLAN = {
    "provider":"TheRundown",
    "secret_name":"EBT_THERUNDOWN_API_KEY",
    "auth_header":"X-TheRundown-Key",
    "base_url":"https://therundown.io/api/v2",
    "plan_name":"FREE",
    "data_delay_verified":True,
    "datapoint_quota_reviewed":True,
    "overage_behavior_reviewed":True,
    "network_enabled":False,
    "authenticated_request_count":0,
    "forecast_enabled":False,
}

class TheRundownAccessContractTests(unittest.TestCase):
    def test_free_is_delayed_and_not_realtime(self):
        info=classify_plan("FREE")
        self.assertEqual(info["delay_seconds"],300)
        self.assertFalse(info["realtime"])

    def test_ultra_is_zero_delay_realtime(self):
        info=classify_plan("ULTRA")
        self.assertEqual(info["delay_seconds"],0)
        self.assertTrue(info["realtime"])

    def test_unknown_plan_fails_closed(self):
        p=dict(PLAN,plan_name="UNKNOWN")
        self.assertTrue(validate_plan(p))

    def test_reviewed_offline_plan_validates(self):
        self.assertEqual(validate_plan(PLAN), [])

    def test_public_reference_endpoints_are_explicit(self):
        self.assertTrue(is_public_reference_path("/api/v2/sports"))
        self.assertTrue(is_public_reference_path("/api/v2/affiliates"))
        self.assertFalse(is_public_reference_path("/api/v2/events/1"))

    def test_delayed_plan_never_becomes_live_model_evidence(self):
        self.assertFalse(can_use_for_live_model_evidence("FREE",0,True,True))
        self.assertFalse(can_use_for_live_model_evidence("PRO",0,True,True))

    def test_realtime_plan_requires_zero_delay_header_and_identity_freshness(self):
        self.assertFalse(can_use_for_live_model_evidence("ULTRA",60,True,True))
        self.assertFalse(can_use_for_live_model_evidence("ULTRA",0,False,True))
        self.assertTrue(can_use_for_live_model_evidence("ULTRA",0,True,True))

    def test_overage_review_is_required(self):
        p=dict(PLAN,overage_behavior_reviewed=False)
        self.assertTrue(validate_plan(p))

    def test_authenticated_request_count_must_stay_zero(self):
        p=dict(PLAN,authenticated_request_count=1)
        self.assertTrue(validate_plan(p))

    def test_offline_phase_never_authorizes_authenticated_request(self):
        self.assertFalse(can_authorize_authenticated_request(PLAN))

if __name__=="__main__":
    unittest.main()
