import copy
import json
import unittest

from provider_activation_gate import (
    activation_eligible,
    provider_ready,
    status,
    validate_config,
)

def base():
    with open("config/provider_readiness.json", encoding="utf-8") as handle:
        return json.load(handle)

def ready_provider(name, role):
    return {
        "name":name,
        "role":role,
        "contract_ready":True,
        "live_auth_verified":True,
        "entitlement_verified":True,
        "identity_verified":True,
        "freshness_verified":True,
        "model_evidence_allowed": role in ("primary_stats","secondary_stats"),
    }

class ProviderActivationGateTests(unittest.TestCase):
    def test_committed_config_is_safe_hold(self):
        c=base()
        self.assertEqual(validate_config(c), [])
        self.assertEqual(status(c), "SAFE_HOLD")
        self.assertFalse(activation_eligible(c))

    def test_no_required_providers_never_activates(self):
        c=base()
        for k in c["model_gates"]: c["model_gates"][k]=True
        self.assertFalse(activation_eligible(c))

    def test_model_gates_are_all_required(self):
        c=base()
        c["required_providers"]=["SportsDataIO"]
        for i,e in enumerate(c["providers"]):
            if e["name"]=="SportsDataIO":
                c["providers"][i]=ready_provider("SportsDataIO","primary_stats")
        for k in c["model_gates"]: c["model_gates"][k]=True
        c["model_gates"]["historical_calibration_verified"]=False
        self.assertFalse(activation_eligible(c))

    def test_primary_stats_provider_is_required(self):
        c=base()
        c["required_providers"]=["WeatherAPI"]
        for i,e in enumerate(c["providers"]):
            if e["name"]=="WeatherAPI":
                c["providers"][i]=ready_provider("WeatherAPI","weather_context")
                c["providers"][i]["identity_verified"]=False
                c["providers"][i]["model_evidence_allowed"]=False
        for k in c["model_gates"]: c["model_gates"][k]=True
        self.assertFalse(activation_eligible(c))

    def test_market_provider_never_counts_as_model_evidence(self):
        e=ready_provider("The Odds API","market_comparison_only")
        e["model_evidence_allowed"]=False
        self.assertTrue(provider_ready(e))
        e["model_evidence_allowed"]=True
        c=base()
        for i,p in enumerate(c["providers"]):
            if p["name"]=="The Odds API": c["providers"][i]=e
        self.assertTrue(validate_config(c))

    def test_aggregator_unresolved_never_ready(self):
        e=ready_provider("RapidAPI","aggregator_unresolved")
        e["model_evidence_allowed"]=False
        self.assertFalse(provider_ready(e))

    def test_ready_primary_plus_all_model_gates_can_be_eligible(self):
        c=base()
        c["required_providers"]=["SportsDataIO"]
        for i,e in enumerate(c["providers"]):
            if e["name"]=="SportsDataIO":
                c["providers"][i]=ready_provider("SportsDataIO","primary_stats")
        for k in c["model_gates"]: c["model_gates"][k]=True
        self.assertTrue(activation_eligible(c))

    def test_missing_provider_coverage_holds(self):
        c=base(); c["providers"].pop()
        self.assertTrue(validate_config(c))
        self.assertFalse(activation_eligible(c))

    def test_duplicate_required_provider_holds(self):
        c=base(); c["required_providers"]=["SportsDataIO","SportsDataIO"]
        self.assertTrue(validate_config(c))

    def test_committed_forecast_toggle_cannot_be_true(self):
        c=base(); c["forecast_enabled"]=True
        self.assertTrue(validate_config(c))

if __name__=="__main__":
    unittest.main()
