import copy
import unittest

from provider_account_evidence import (
    gap_report,
    load_registry,
    validate_registry,
)

class ProviderAccountEvidenceTests(unittest.TestCase):
    def test_committed_registry_is_valid_and_hold(self):
        registry=load_registry()
        self.assertEqual(validate_registry(registry),[])
        result=gap_report(registry)
        self.assertEqual(result["status"],"ACCOUNT_EVIDENCE_HOLD")
        self.assertFalse(result["live_request_permitted"])
        self.assertFalse(result["model_evidence_allowed"])
        self.assertEqual(set(result["gaps"]),{"SportsDataIO","Sportradar","RapidAPI"})
        self.assertGreater(len(result["gaps"]["SportsDataIO"]),0)
        self.assertGreater(len(result["gaps"]["Sportradar"]),0)
        self.assertGreater(len(result["gaps"]["RapidAPI"]),0)

    def test_sensitive_fields_are_forbidden(self):
        registry=load_registry()
        bad=copy.deepcopy(registry)
        bad["providers"][0]["api_key"]="do-not-store"
        self.assertIn(
            "sensitive field forbidden in account evidence registry",
            validate_registry(bad),
        )

    def test_sportsdataio_hint_is_not_entitlement(self):
        registry=load_registry()
        sd=next(p for p in registry["providers"] if p["name"]=="SportsDataIO")
        self.assertEqual(sd["account_tier"],"FREE_TRIAL")
        self.assertTrue(sd["account_tier_verified"])
        self.assertEqual(sd["account_product_hint"],"NFL")
        self.assertFalse(sd["product_hint_entitlement_proof"])
        self.assertEqual(sd["provider_docs_scope_status"],"CONFLICTING")
        self.assertFalse(sd["live_request_permitted"])
        self.assertFalse(sd["model_evidence_allowed"])

    def test_sportradar_account_existence_does_not_grant_product(self):
        registry=load_registry()
        sp=next(p for p in registry["providers"] if p["name"]=="Sportradar")
        self.assertTrue(sp["account_exists"])
        self.assertFalse(sp["subscription_details_verified"])
        self.assertFalse(sp["exact_product_verified"])
        self.assertFalse(sp["access_level_verified"])
        self.assertFalse(sp["quota_verified"])
        self.assertFalse(sp["live_request_permitted"])

    def test_rapidapi_signin_does_not_grant_route(self):
        registry=load_registry()
        ra=next(p for p in registry["providers"] if p["name"]=="RapidAPI")
        self.assertTrue(ra["account_exists"])
        self.assertFalse(ra["subscription_inventory_verified"])
        self.assertFalse(ra["exact_product_verified"])
        self.assertFalse(ra["exact_host_verified"])
        self.assertFalse(ra["exact_plan_verified"])
        self.assertFalse(ra["route_binding_verified"])
        self.assertFalse(ra["live_request_permitted"])

    def test_invalid_live_request_claims_fail_closed(self):
        registry=load_registry()

        bad=copy.deepcopy(registry)
        sd=next(p for p in bad["providers"] if p["name"]=="SportsDataIO")
        sd["live_request_permitted"]=True
        self.assertTrue(validate_registry(bad))

        bad=copy.deepcopy(registry)
        sp=next(p for p in bad["providers"] if p["name"]=="Sportradar")
        sp["live_request_permitted"]=True
        self.assertTrue(validate_registry(bad))

        bad=copy.deepcopy(registry)
        ra=next(p for p in bad["providers"] if p["name"]=="RapidAPI")
        ra["live_request_permitted"]=True
        self.assertTrue(validate_registry(bad))

if __name__=="__main__":
    unittest.main()
