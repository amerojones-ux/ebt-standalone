import copy
import json
import unittest

from provider_contract_reconciliation import REGISTRY, summary, validate_configs
from provider_preflight import PROVIDERS

def load_all():
    data={}
    for provider_id,spec in REGISTRY.items():
        with open(spec["path"],encoding="utf-8") as handle:
            data[spec["path"]]=json.load(handle)
    return data

class ProviderContractReconciliationTests(unittest.TestCase):
    def test_committed_configs_reconcile(self):
        self.assertEqual(validate_configs(),[])
        self.assertEqual(summary()["status"],"SAFE_HOLD")
        self.assertEqual(summary()["provider_count"],7)

    def test_registry_exactly_matches_preflight_provider_ids(self):
        self.assertEqual(set(REGISTRY),set(PROVIDERS))

    def test_each_secret_name_matches_canonical_mapping(self):
        data=load_all()
        for provider_id,spec in REGISTRY.items():
            self.assertEqual(data[spec["path"]]["secret_name"],PROVIDERS[provider_id])

    def test_secret_mapping_drift_is_detected(self):
        data=load_all()
        path=REGISTRY["ODDS"]["path"]
        data[path]["secret_name"]="WRONG"
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_network_enable_drift_is_detected(self):
        data=load_all()
        path=REGISTRY["APISPORTS"]["path"]
        data[path]["network_enabled"]=True
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_forecast_enable_drift_is_detected(self):
        data=load_all()
        path=REGISTRY["SPORTSDATA"]["path"]
        data[path]["forecast_enabled"]=True
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_nonzero_request_drift_is_detected(self):
        data=load_all()
        path=REGISTRY["SPORTRADAR"]["path"]
        data[path]["request_count"]=1
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_boolean_is_not_accepted_as_zero_request_count(self):
        data=load_all()
        path=REGISTRY["ODDS"]["path"]
        data[path]["request_count"]=False
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_provider_display_drift_is_detected(self):
        data=load_all()
        path=REGISTRY["RAPID"]["path"]
        data[path]["provider"]="Rapid API"
        self.assertTrue(validate_configs(loader=lambda p:data[p]))

    def test_unreadable_config_is_detected(self):
        self.assertTrue(validate_configs(loader=lambda p: (_ for _ in ()).throw(OSError("x"))))

if __name__=="__main__":
    unittest.main()
