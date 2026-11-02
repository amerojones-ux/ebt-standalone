import unittest

from sportsdataio_access_contract import (
    classify_access,
    validate_auth_config,
    can_promote_to_model_evidence,
)

class SportsDataIoAccessContractTests(unittest.TestCase):
    def test_free_trial_is_scrambled_and_not_evidence(self):
        info=classify_access("FREE_TRIAL")
        self.assertEqual(info["data_class"], "scrambled")
        self.assertFalse(info["model_evidence_allowed"])

    def test_dev_key_is_still_scrambled(self):
        self.assertEqual(classify_access("DEV_KEY")["data_class"], "scrambled")

    def test_replay_is_historical_not_current(self):
        info=classify_access("REPLAY")
        self.assertTrue(info["historical_real"])
        self.assertFalse(info["live_current"])

    def test_discovery_lab_paid_is_delayed(self):
        info=classify_access("DISCOVERY_LAB_PAID")
        self.assertEqual(info["data_class"], "real_next_day_delayed")
        self.assertFalse(info["live_current"])

    def test_unknown_fails_closed(self):
        self.assertEqual(classify_access("mystery")["data_class"], "unknown")

    def test_header_auth_config(self):
        config={
            "secret_name":"EBT_SPORTSDATA_API_KEY",
            "auth_header":"Ocp-Apim-Subscription-Key",
            "allow_query_key":False,
            "network_enabled":False,
            "forecast_enabled":False,
        }
        self.assertEqual(validate_auth_config(config), [])

    def test_query_key_rejected(self):
        config={
            "secret_name":"EBT_SPORTSDATA_API_KEY",
            "auth_header":"Ocp-Apim-Subscription-Key",
            "allow_query_key":True,
            "network_enabled":False,
            "forecast_enabled":False,
        }
        self.assertTrue(validate_auth_config(config))

    def test_production_not_auto_promoted(self):
        self.assertFalse(can_promote_to_model_evidence("LEAGUES_PRODUCTION"))

    def test_production_requires_all_three_independent_gates(self):
        self.assertFalse(can_promote_to_model_evidence("LEAGUES_PRODUCTION", True, True, False))
        self.assertTrue(can_promote_to_model_evidence("LEAGUES_PRODUCTION", True, True, True))

    def test_nonproduction_never_promotes_even_with_flags(self):
        self.assertFalse(can_promote_to_model_evidence("FREE_TRIAL", True, True, True))
        self.assertFalse(can_promote_to_model_evidence("REPLAY", True, True, True))

if __name__ == "__main__":
    unittest.main()
