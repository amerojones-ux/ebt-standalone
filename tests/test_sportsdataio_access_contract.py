import unittest

from sportsdataio_access_contract import (
    classify_access,
    validate_auth_config,
    can_promote_to_model_evidence,
    can_promote_to_schedule_evidence,
    free_trial_probe_blockers,
)

class SportsDataIoAccessContractTests(unittest.TestCase):
    def test_free_trial_is_scrambled_and_not_evidence(self):
        info=classify_access("FREE_TRIAL")
        self.assertEqual(info["data_class"], "scrambled")
        self.assertFalse(info["model_evidence_allowed"])

    def test_free_trial_scope_conflict_is_explicit_probe_blocker(self):
        config={
            "declared_access_method":"FREE_TRIAL",
            "account_access_confirmed":True,
            "scrambled_data_acknowledged":True,
            "official_scope_status":"CONFLICTING",
            "trial_scope_reconciled":False,
        }
        blockers=free_trial_probe_blockers(config)
        self.assertIn("official Free Trial scope conflict unresolved",blockers)
        self.assertIn("Free Trial scope not reconciled",blockers)

    def test_reconciled_free_trial_scope_clears_only_scope_blockers(self):
        config={
            "declared_access_method":"FREE_TRIAL",
            "account_access_confirmed":True,
            "scrambled_data_acknowledged":True,
            "official_scope_status":"RECONCILED",
            "trial_scope_reconciled":True,
        }
        self.assertEqual(free_trial_probe_blockers(config),[])

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

    def test_free_trial_model_evidence_flag_is_invalid_config(self):
        config={
            "secret_name":"EBT_SPORTSDATA_API_KEY",
            "auth_header":"Ocp-Apim-Subscription-Key",
            "allow_query_key":False,
            "network_enabled":False,
            "forecast_enabled":False,
            "declared_access_method":"FREE_TRIAL",
            "model_evidence_allowed":True,
            "official_scope_status":"CONFLICTING",
            "trial_scope_reconciled":False,
        }
        errors=validate_auth_config(config)
        self.assertIn("Free Trial model evidence must remain disabled",errors)

    def test_conflicting_scope_cannot_be_marked_reconciled(self):
        config={
            "secret_name":"EBT_SPORTSDATA_API_KEY",
            "auth_header":"Ocp-Apim-Subscription-Key",
            "allow_query_key":False,
            "network_enabled":False,
            "forecast_enabled":False,
            "declared_access_method":"FREE_TRIAL",
            "model_evidence_allowed":False,
            "official_scope_status":"CONFLICTING",
            "trial_scope_reconciled":True,
        }
        errors=validate_auth_config(config)
        self.assertIn("conflicting scope cannot be marked reconciled",errors)

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

    def test_global_production_never_promotes_to_generic_model_evidence(self):
        self.assertFalse(can_promote_to_model_evidence("GLOBAL_PRODUCTION", True, True, True))

    def test_global_production_can_only_promote_to_schedule_evidence(self):
        self.assertTrue(can_promote_to_schedule_evidence("GLOBAL_PRODUCTION", True, True, True))

    def test_method_normalization_is_consistent(self):
        self.assertTrue(can_promote_to_model_evidence("  leagues_production  ", True, True, True))

if __name__ == "__main__":
    unittest.main()
