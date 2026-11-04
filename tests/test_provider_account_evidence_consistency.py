import copy
import json
import unittest

from provider_account_evidence import load_registry
from provider_account_evidence_consistency import (
    CONFIGS,
    validate_consistency,
)

def load_configs():
    out={}
    for provider,path in CONFIGS.items():
        with open(path,encoding="utf-8") as handle:
            out[path]=json.load(handle)
    return out

class ProviderAccountEvidenceConsistencyTests(unittest.TestCase):
    def test_committed_state_is_consistent(self):
        self.assertEqual(validate_consistency(),[])

    def test_sportsdataio_scope_cannot_be_reconciled_without_registry_support(self):
        configs=load_configs()
        configs[CONFIGS["SportsDataIO"]]["trial_scope_reconciled"]=True
        errors=validate_consistency(
            config_loader=lambda path:configs[path],
        )
        self.assertIn("SportsDataIO scope reconciliation unsupported",errors)

    def test_sportradar_product_claim_requires_account_evidence(self):
        configs=load_configs()
        configs[CONFIGS["Sportradar"]]["product_verified"]=True
        errors=validate_consistency(
            config_loader=lambda path:configs[path],
        )
        self.assertIn("Sportradar product_verified unsupported",errors)

    def test_rapidapi_product_and_host_claims_require_account_evidence(self):
        configs=load_configs()
        cfg=configs[CONFIGS["RapidAPI"]]
        cfg["api_product"]="Example"
        cfg["rapidapi_host"]="example.p.rapidapi.com"
        errors=validate_consistency(
            config_loader=lambda path:configs[path],
        )
        self.assertIn("RapidAPI product name unsupported",errors)
        self.assertIn("RapidAPI host unsupported",errors)

    def test_matching_account_evidence_allows_future_verified_metadata(self):
        registry=copy.deepcopy(load_registry())
        configs=load_configs()

        sp=next(p for p in registry["providers"] if p["name"]=="Sportradar")
        sp.update({
            "subscription_details_verified":True,
            "product_inventory_verified":True,
            "exact_product_verified":True,
            "access_level_verified":True,
            "quota_verified":True,
        })
        spcfg=configs[CONFIGS["Sportradar"]]
        spcfg.update({
            "subscription_details_verified":True,
            "product_inventory_verified":True,
            "product_verified":True,
            "access_level_verified":True,
            "quota_reviewed":True,
        })

        ra=next(p for p in registry["providers"] if p["name"]=="RapidAPI")
        ra.update({
            "subscription_inventory_verified":True,
            "subscription_verified":True,
            "route_binding_verified":True,
            "exact_product_verified":True,
            "exact_host_verified":True,
            "exact_plan_verified":True,
            "billing_object_verified":True,
            "quota_verified":True,
            "overage_verified":True,
            "exact_endpoint_verified":True,
        })
        racfg=configs[CONFIGS["RapidAPI"]]
        racfg.update({
            "subscription_inventory_verified":True,
            "subscription_verified":True,
            "route_binding_verified":True,
            "api_product":"Example",
            "rapidapi_host":"example.p.rapidapi.com",
            "plan_name":"Basic",
            "billing_object":"request",
            "probe_endpoint":"https://example.p.rapidapi.com/v1/status",
            "quota_reviewed":True,
            "overage_reviewed":True,
            "endpoint_reviewed":True,
        })

        self.assertEqual(
            validate_consistency(
                registry=registry,
                config_loader=lambda path:configs[path],
            ),
            [],
        )

if __name__=="__main__":
    unittest.main()
