import copy
import json
import unittest

from remaining_provider_probe_preconditions import (
    FILES,
    assess_all,
    assess_rapidapi,
    assess_sportradar,
    assess_sportsdataio,
)

def load_configs():
    out={}
    for provider,path in FILES.items():
        with open(path,encoding="utf-8") as handle:
            out[path]=json.load(handle)
    return out

class RemainingProviderProbePreconditionTests(unittest.TestCase):
    def test_committed_state_is_blocked_safe(self):
        result=assess_all()
        self.assertEqual(result["status"],"BLOCKED_SAFE")
        self.assertEqual(result["provider_count"],3)
        self.assertFalse(result["network_request_permitted"])
        for provider in result["providers"]:
            self.assertEqual(provider["status"],"BLOCKED_PRECONDITION")
            self.assertFalse(provider["network_request_permitted"])
            self.assertFalse(provider["secret_access_permitted"])
            self.assertFalse(provider["forecast_activation_permitted"])
            self.assertGreater(len(provider["blockers"]),0)

    def test_committed_sportsdataio_free_trial_stays_blocked_by_scope_conflict(self):
        cfg=load_configs()[FILES["SportsDataIO"]]
        self.assertEqual(cfg["declared_access_method"],"FREE_TRIAL")
        result=assess_sportsdataio(cfg)
        self.assertEqual(result["status"],"BLOCKED_PRECONDITION")
        self.assertIn(
            "official Free Trial scope conflict unresolved",
            result["blockers"],
        )
        self.assertIn("Free Trial scope not reconciled",result["blockers"])

    def test_free_trial_complete_route_still_blocks_until_scope_reconciled(self):
        cfg=load_configs()[FILES["SportsDataIO"]]
        cfg.update({
            "probe_product":"NFL League API",
            "probe_endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        result=assess_sportsdataio(cfg)
        self.assertEqual(result["status"],"BLOCKED_PRECONDITION")
        self.assertIn(
            "official Free Trial scope conflict unresolved",
            result["blockers"],
        )

    def test_reconciled_free_trial_route_requires_hardened_implementation_but_not_model_evidence(self):
        cfg=load_configs()[FILES["SportsDataIO"]]
        cfg.update({
            "official_scope_status":"RECONCILED",
            "trial_scope_reconciled":True,
            "probe_product":"NFL League API",
            "probe_endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        result=assess_sportsdataio(cfg)
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")
        self.assertEqual(result["blockers"],[])
        self.assertFalse(cfg["model_evidence_allowed"])

    def test_sportsdataio_complete_route_requires_implementation(self):
        cfg=load_configs()[FILES["SportsDataIO"]]
        cfg.update({
            "declared_access_method":"LEAGUES_PRODUCTION",
            "probe_product":"NFL League API",
            "probe_endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        result=assess_sportsdataio(cfg)
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")
        self.assertEqual(result["blockers"],[])

    def test_sportsdataio_query_key_endpoint_is_rejected(self):
        cfg=load_configs()[FILES["SportsDataIO"]]
        cfg.update({
            "declared_access_method":"LEAGUES_PRODUCTION",
            "probe_product":"NFL League API",
            "probe_endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress?key=x",
            "quota_reviewed":True,
            "overage_reviewed":True,
        })
        result=assess_sportsdataio(cfg)
        self.assertIn(
            "exact header-auth probe endpoint not reviewed",
            result["blockers"],
        )

    def test_committed_sportradar_account_exists_but_subscription_stays_blocked(self):
        cfg=load_configs()[FILES["Sportradar"]]
        self.assertTrue(cfg["account_registration_confirmed"])
        result=assess_sportradar(cfg)
        self.assertEqual(result["status"],"BLOCKED_PRECONDITION")
        self.assertIn(
            "Sportradar product subscription details not verified",
            result["blockers"],
        )
        self.assertIn(
            "Sportradar access level not verified from account",
            result["blockers"],
        )

    def test_committed_rapidapi_signin_exists_but_route_stays_blocked(self):
        cfg=load_configs()[FILES["RapidAPI"]]
        self.assertTrue(cfg["account_signin_confirmed"])
        result=assess_rapidapi(cfg)
        self.assertEqual(result["status"],"BLOCKED_PRECONDITION")
        self.assertIn(
            "RapidAPI subscription inventory not verified",
            result["blockers"],
        )
        self.assertIn(
            "RapidAPI product-to-host route binding not verified",
            result["blockers"],
        )

    def test_sportradar_trial_route_requires_implementation(self):
        cfg=load_configs()[FILES["Sportradar"]]
        cfg.update({
            "access_level":"trial",
            "subscription_details_verified":True,
            "product_inventory_verified":True,
            "access_level_verified":True,
            "product_name":"NFL Base",
            "product_verified":True,
            "quota_reviewed":True,
            "probe_endpoint":"https://api.sportradar.com/nfl/official/trial/v7/en/league/hierarchy.json",
        })
        result=assess_sportradar(cfg)
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")
        self.assertEqual(result["blockers"],[])

    def test_sportradar_access_level_endpoint_must_match(self):
        cfg=load_configs()[FILES["Sportradar"]]
        cfg.update({
            "access_level":"production",
            "product_name":"NFL Base",
            "product_verified":True,
            "quota_reviewed":True,
            "probe_endpoint":"https://api.sportradar.com/nfl/official/trial/v7/en/league/hierarchy.json",
        })
        result=assess_sportradar(cfg)
        self.assertIn(
            "access-level-specific League Hierarchy endpoint not reviewed",
            result["blockers"],
        )

    def test_rapidapi_complete_route_requires_implementation(self):
        cfg=load_configs()[FILES["RapidAPI"]]
        cfg.update({
            "subscription_inventory_verified":True,
            "route_binding_verified":True,
            "api_product":"Example Sports Provider",
            "rapidapi_host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"request",
            "subscription_verified":True,
            "quota_reviewed":True,
            "overage_reviewed":True,
            "endpoint_reviewed":True,
        })
        result=assess_rapidapi(cfg)
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")
        self.assertEqual(result["blockers"],[])

    def test_network_enable_is_invalid_hold(self):
        cfg=load_configs()[FILES["RapidAPI"]]
        cfg["network_enabled"]=True
        result=assess_rapidapi(cfg)
        self.assertEqual(result["status"],"INVALID_HOLD")

    def test_overall_ready_transition_fails_closed(self):
        configs=load_configs()
        cfg=configs[FILES["Sportradar"]]
        cfg.update({
            "access_level":"trial",
            "product_name":"NFL Base",
            "product_verified":True,
            "quota_reviewed":True,
            "probe_endpoint":"https://api.sportradar.com/nfl/official/trial/v7/en/league/hierarchy.json",
        })
        result=assess_all(loader=lambda path:configs[path])
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")

if __name__=="__main__":
    unittest.main()
