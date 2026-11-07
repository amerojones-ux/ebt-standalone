"""Synthetic tests for automated opportunity-discovery readiness."""
import json
import unittest
from pathlib import Path

from extensions.discovery_readiness import assess_discovery_readiness

ROOT = Path(__file__).resolve().parents[1]


def provider_state():
    return {
        "providers": [
            {
                "name": name, "contract_ready": True, "live_auth_verified": True,
                "entitlement_verified": False, "identity_verified": False,
                "freshness_verified": False, "model_evidence_allowed": False,
            }
            for name in ("TheRundown","The Odds API","RapidAPI")
        ]
    }


def module_state(*,quotes=False,role=False,stats=False,calibration=False):
    return {
        "extensions": {
            "alternate_line_opportunity_discovery":{"code":"implemented"},
            "role_reallocation_trigger":{"code":"implemented"},
            "rare_event_asymmetric_value":{"code":"implemented"},
        },
        "live_integrations": {
            "sportsbook_quote": quotes,
            "official_slate_and_role": role,
            "licensed_player_and_team_stats": stats,
            "calibrated_models": calibration,
            "production_api": False,
        },
    }


class DiscoveryReadinessTests(unittest.TestCase):
    def test_current_repository_configs_fail_closed(self):
        providers=json.loads((ROOT/"config/provider_readiness.json").read_text())
        modules=json.loads((ROOT/"config/module_readiness_2026_10_30.json").read_text())
        rundown=json.loads((ROOT/"config/therundown_access.json").read_text())
        odds=json.loads((ROOT/"config/theoddsapi_prop_ladder.json").read_text())
        rapid=json.loads((ROOT/"config/rapidapi_routing.json").read_text())
        out=assess_discovery_readiness(
            providers,modules,therundown_access=rundown,
            theoddsapi_prop_ladder=odds,rapidapi_routing=rapid)
        self.assertEqual(out["status"],"SAFE_HOLD")
        self.assertFalse(out["market_ladder_ready"])
        self.assertEqual(out["eligible_market_sources"],[])
        self.assertIn("NO_ELIGIBLE_REALTIME_COMPLETE_PROP_LADDER_SOURCE",out["blockers"])
        self.assertTrue(all(not row["automated_input_ready"] for row in out["lanes"].values()))
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_live_auth_alone_never_establishes_market_coverage(self):
        providers=provider_state()
        rundown={
            "plan_name":"ULTRA","network_enabled":True,"forecast_enabled":True,
        }
        odds={
            "network_enabled":True,"forecast_enabled":True,"path":"/v4/sports",
            "account_plan_verified":False,"quota_cost_reviewed":False,"entitlement_verified":False,"identity_mapping_verified":False,"freshness_verified":False,"market_ladder_route_verified":True,"complete_posted_player_prop_ladder_verified":False,
        }
        rapid={
            "network_enabled":True,"forecast_enabled":True,"probe_endpoint":"/odds",
            "account_plan_verified":False,"quota_cost_reviewed":False,"entitlement_verified":False,"identity_mapping_verified":False,"freshness_verified":False,"market_ladder_route_verified":True,"complete_posted_player_prop_ladder_verified":False,
        }
        out=assess_discovery_readiness(
            providers,module_state(quotes=True,role=True,stats=True),
            therundown_access=rundown,theoddsapi_prop_ladder=odds,rapidapi_routing=rapid)
        self.assertEqual(out["eligible_market_sources"],[])
        self.assertFalse(out["market_ladder_ready"])

    def test_rundown_free_plan_cannot_claim_prop_ladder(self):
        providers=provider_state()
        for row in providers["providers"]:
            if row["name"]=="TheRundown":
                row.update(entitlement_verified=True,identity_verified=True,freshness_verified=True)
        rundown={"plan_name":"FREE","network_enabled":True,"forecast_enabled":True}
        odds={"network_enabled":False,"forecast_enabled":False,"event_odds_path_template":"/v4/sports/{sport}/events/{eventId}/odds","event_markets_path_template":"/v4/sports/{sport}/events/{eventId}/markets"}
        rapid={"network_enabled":False,"forecast_enabled":False,"probe_endpoint":""}
        out=assess_discovery_readiness(
            providers,module_state(quotes=True,role=True,stats=True),
            therundown_access=rundown,theoddsapi_prop_ladder=odds,rapidapi_routing=rapid)
        diag=next(x for x in out["market_source_diagnostics"] if x["provider"]=="TheRundown")
        self.assertFalse(diag["eligible"])
        self.assertIn("configured plan does not include props",diag["blockers"])

    def test_fully_verified_realtime_prop_source_can_clear_input_coverage(self):
        providers=provider_state()
        for row in providers["providers"]:
            if row["name"]=="TheRundown":
                row.update(entitlement_verified=True,identity_verified=True,freshness_verified=True)
        rundown={"plan_name":"ULTRA","network_enabled":True,"forecast_enabled":True}
        odds={"network_enabled":False,"forecast_enabled":False,"event_odds_path_template":"/v4/sports/{sport}/events/{eventId}/odds","event_markets_path_template":"/v4/sports/{sport}/events/{eventId}/markets"}
        rapid={"network_enabled":False,"forecast_enabled":False,"probe_endpoint":""}
        out=assess_discovery_readiness(
            providers,module_state(quotes=True,role=True,stats=True,calibration=True),
            therundown_access=rundown,theoddsapi_prop_ladder=odds,rapidapi_routing=rapid)
        self.assertEqual(out["eligible_market_sources"],["TheRundown"])
        self.assertTrue(out["market_ladder_ready"])
        self.assertTrue(all(row["automated_input_ready"] for row in out["lanes"].values()))
        self.assertEqual(out["status"],"READY_FOR_AUTOMATED_RESEARCH")
        self.assertTrue(out["candidate_qualification_still_required"])
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_generic_adapter_needs_explicit_ladder_verification(self):
        providers=provider_state()
        for row in providers["providers"]:
            if row["name"]=="The Odds API":
                row.update(entitlement_verified=True,identity_verified=True,freshness_verified=True)
        odds={
            "network_enabled":True,"forecast_enabled":True,
            "event_odds_path_template":"/v4/sports/{sport}/events/{eventId}/odds",
            "event_markets_path_template":"/v4/sports/{sport}/events/{eventId}/markets",
            "account_plan_verified":True,"quota_cost_reviewed":True,
            "entitlement_verified":True,"identity_mapping_verified":True,
            "freshness_verified":True,"market_ladder_route_verified":True,
            "complete_posted_player_prop_ladder_verified":False,
        }
        rundown={"plan_name":"FREE","network_enabled":False,"forecast_enabled":False}
        rapid={"network_enabled":False,"forecast_enabled":False,"probe_endpoint":""}
        out=assess_discovery_readiness(
            providers,module_state(quotes=True,role=True,stats=True),
            therundown_access=rundown,theoddsapi_prop_ladder=odds,rapidapi_routing=rapid)
        diag=next(x for x in out["market_source_diagnostics"] if x["provider"]=="The Odds API")
        self.assertFalse(diag["eligible"])
        self.assertIn("complete posted player-prop ladder not verified",diag["blockers"])

    def test_ready_inputs_do_not_equal_candidate_approval(self):
        providers=provider_state()
        for row in providers["providers"]:
            if row["name"]=="TheRundown":
                row.update(entitlement_verified=True,identity_verified=True,freshness_verified=True)
        out=assess_discovery_readiness(
            providers,module_state(quotes=True,role=True,stats=True,calibration=True),
            therundown_access={"plan_name":"ULTRA","network_enabled":True,"forecast_enabled":True},
            theoddsapi_prop_ladder={"network_enabled":False,"forecast_enabled":False,"event_odds_path_template":"/v4/sports/{sport}/events/{eventId}/odds","event_markets_path_template":"/v4/sports/{sport}/events/{eventId}/markets"},
            rapidapi_routing={"network_enabled":False,"forecast_enabled":False,"probe_endpoint":""})
        self.assertEqual(out["forecast_status"],"HOLD")
        self.assertEqual(out["wager_status"],"NOT APPROVED")
        self.assertTrue(out["candidate_qualification_still_required"])


if __name__=="__main__":
    unittest.main()
