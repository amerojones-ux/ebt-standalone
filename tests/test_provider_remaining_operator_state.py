import copy
import unittest

from provider_account_evidence import load_registry
from provider_account_metadata_transition import build_transition, load_configs
from provider_remaining_operator_state import (
    METADATA_WORKFLOWS,
    PROBE_WORKFLOWS,
    assess_remaining_provider_state,
)

def current_readiness():
    import json
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/"config/provider_readiness.json"
    return json.loads(path.read_text(encoding="utf-8"))

def completed_state(provider):
    facts_by_provider={
        "SportsDataIO":{
            "source_type":"PROVIDER_SUPPORT",
            "scope_status":"RECONCILED",
            "product_name":"NFL League API",
            "feed_scope":"Scores",
            "endpoint":"https://api.sportsdata.io/v3/nfl/scores/json/AreAnyGamesInProgress",
            "quota_reviewed":True,
            "overage_reviewed":True,
        },
        "Sportradar":{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"NFL API",
            "package_name":"NFL Base",
            "access_level":"trial",
            "quota_reviewed":True,
        },
        "RapidAPI":{
            "source_type":"ACCOUNT_PORTAL",
            "product_name":"Example Sports Provider",
            "host":"example-sports.p.rapidapi.com",
            "pricing_type":"FREE",
            "plan_name":"Basic",
            "billing_object":"Requests",
            "endpoint":"https://example-sports.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
        },
    }
    transition=build_transition(provider,facts_by_provider[provider])
    assert transition["status"]=="VALID_ACCOUNT_METADATA_TRANSITION_PREVIEW",transition
    return transition["candidate_registry"],transition["candidate_configs"]

class RemainingProviderOperatorStateTests(unittest.TestCase):
    def test_current_repository_state_is_exact_safe_hold(self):
        result=assess_remaining_provider_state()
        self.assertEqual(result["status"],"SAFE_HOLD")
        self.assertEqual(result["overall_provider_count"],7)
        self.assertEqual(result["overall_live_auth_verified_count"],4)
        self.assertEqual(result["remaining_provider_count"],3)
        self.assertEqual(result["remaining_live_auth_verified_count"],0)
        by_name={row["provider"]:row for row in result["providers"]}
        self.assertEqual(set(by_name),{"SportsDataIO","Sportradar","RapidAPI"})
        for name,row in by_name.items():
            with self.subTest(provider=name):
                self.assertEqual(row["status"],"ACCOUNT_METADATA_REQUIRED")
                self.assertEqual(row["next_stage"],"SIGNED_ACCOUNT_METADATA_CLAIM")
                self.assertEqual(row["next_workflow"],METADATA_WORKFLOWS[name])
                self.assertTrue(row["missing_metadata"])
                self.assertFalse(row["probe_workflow_present"])
                self.assertIn("provider_network_request",row["blocked_actions"])
                self.assertIn("forecast_activation",row["blocked_actions"])

    def test_completed_metadata_without_probe_requires_probe_engineering(self):
        for provider in ("SportsDataIO","Sportradar","RapidAPI"):
            with self.subTest(provider=provider):
                registry,configs=completed_state(provider)
                result=assess_remaining_provider_state(
                    readiness=current_readiness(),
                    registry=registry,
                    configs=configs,
                    path_exists=lambda path:path in METADATA_WORKFLOWS.values(),
                )
                row=next(x for x in result["providers"] if x["provider"]==provider)
                self.assertEqual(
                    row["status"],
                    "METADATA_PERSISTED_PROBE_ENGINEERING_REQUIRED",
                )
                self.assertEqual(
                    row["next_stage"],
                    "HARDENED_ONE_SHOT_PROBE_ENGINEERING",
                )
                self.assertIsNone(row["next_workflow"])
                self.assertEqual(row["missing_metadata"],[])
                self.assertFalse(row["probe_workflow_present"])

    def test_completed_metadata_plus_probe_reaches_explicit_auth_gate_only(self):
        for provider in ("SportsDataIO","Sportradar","RapidAPI"):
            with self.subTest(provider=provider):
                registry,configs=completed_state(provider)
                result=assess_remaining_provider_state(
                    readiness=current_readiness(),
                    registry=registry,
                    configs=configs,
                    path_exists=lambda path:True,
                )
                row=next(x for x in result["providers"] if x["provider"]==provider)
                self.assertEqual(
                    row["status"],
                    "PROBE_PREPARED_AWAITING_EXPLICIT_AUTHORIZATION",
                )
                self.assertEqual(
                    row["next_stage"],
                    "EXPLICIT_ONE_SHOT_REQUEST_AUTHORIZATION",
                )
                self.assertEqual(row["next_workflow"],PROBE_WORKFLOWS[provider])
                self.assertIn("provider_network_request",row["blocked_actions"])

    def test_live_auth_flag_with_incomplete_metadata_is_invalid_hold(self):
        readiness=current_readiness()
        target=next(x for x in readiness["providers"] if x["name"]=="SportsDataIO")
        target["live_auth_verified"]=True
        result=assess_remaining_provider_state(
            readiness=readiness,
            registry=load_registry(),
            configs=load_configs(),
        )
        row=next(x for x in result["providers"] if x["provider"]=="SportsDataIO")
        self.assertEqual(result["status"],"INVALID_HOLD")
        self.assertEqual(row["status"],"INVALID_HOLD")
        self.assertIn(
            "live_auth_verified without complete account metadata",
            row["errors"],
        )

    def test_network_or_forecast_enablement_forces_invalid_hold(self):
        configs=copy.deepcopy(load_configs())
        configs["RapidAPI"]["network_enabled"]=True
        result=assess_remaining_provider_state(
            readiness=current_readiness(),
            registry=load_registry(),
            configs=configs,
        )
        row=next(x for x in result["providers"] if x["provider"]=="RapidAPI")
        self.assertEqual(result["status"],"INVALID_HOLD")
        self.assertEqual(row["status"],"INVALID_HOLD")
        self.assertIn("provider config network_enabled unexpectedly true",row["errors"])

    def test_metadata_workflow_missing_for_required_provider_is_invalid(self):
        def exists(path):
            return path!=METADATA_WORKFLOWS["Sportradar"]
        result=assess_remaining_provider_state(path_exists=exists)
        row=next(x for x in result["providers"] if x["provider"]=="Sportradar")
        self.assertEqual(result["status"],"INVALID_HOLD")
        self.assertEqual(row["status"],"INVALID_HOLD")
        self.assertIn("metadata claim workflow missing",row["errors"])

if __name__=="__main__":
    unittest.main()
