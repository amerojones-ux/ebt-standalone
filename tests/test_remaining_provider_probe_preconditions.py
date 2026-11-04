import copy
import json
import unittest

from remaining_provider_probe_preconditions import (
    FILES,
    assess_all,
    assess_rapidapi,
    assess_sportradar,
    assess_sportsdataio,
    assess_therundown,
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
        self.assertEqual(result["provider_count"],4)
        self.assertFalse(result["network_request_permitted"])
        for provider in result["providers"]:
            self.assertEqual(provider["status"],"BLOCKED_PRECONDITION")
            self.assertFalse(provider["network_request_permitted"])
            self.assertFalse(provider["secret_access_permitted"])
            self.assertFalse(provider["forecast_activation_permitted"])
            self.assertGreater(len(provider["blockers"]),0)

    def test_therundown_complete_account_review_requires_implementation(self):
        cfg=load_configs()[FILES["TheRundown"]]
        cfg.update({
            "plan_name":"FREE",
            "data_delay_verified":True,
            "datapoint_quota_reviewed":True,
            "overage_behavior_reviewed":True,
        })
        result=assess_therundown(cfg)
        self.assertEqual(result["status"],"IMPLEMENTATION_REQUIRED")
        self.assertEqual(result["blockers"],[])

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

    def test_sportradar_trial_route_requires_implementation(self):
        cfg=load_configs()[FILES["Sportradar"]]
        cfg.update({
            "access_level":"trial",
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
        cfg=load_configs()[FILES["TheRundown"]]
        cfg["network_enabled"]=True
        result=assess_therundown(cfg)
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
