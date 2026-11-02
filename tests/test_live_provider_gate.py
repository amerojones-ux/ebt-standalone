import copy
import unittest
from live_provider_gate import validate
from provider_preflight import PROVIDERS

def valid():
    return {"network_enabled": False, "forecast_enabled": False,
        "providers": [{"name": name, "secret_name": secret, "approved": False,
        "product": None, "host": None, "path": None, "auth_method": None,
        "quota_per_day": None, "cost_per_call_usd": None, "reviewer": None,
        "approved_at": None} for name, secret in PROVIDERS.items()]}

class LiveProviderGateTests(unittest.TestCase):
    def test_safe_hold(self): self.assertEqual(validate(valid()), [])
    def test_network_enabled(self):
        r=valid(); r["network_enabled"]=True; self.assertTrue(validate(r))
    def test_forecast_enabled(self):
        r=valid(); r["forecast_enabled"]=True; self.assertTrue(validate(r))
    def test_approval_attempt(self):
        r=valid(); r["providers"][0]["approved"]=True; self.assertTrue(validate(r))
    def test_partial_metadata(self):
        r=valid(); r["providers"][0]["host"]="example.com"; self.assertTrue(validate(r))
    def test_missing_provider(self):
        r=valid(); r["providers"].pop(); self.assertTrue(validate(r))
    def test_duplicate_provider(self):
        r=valid(); r["providers"][1]=copy.deepcopy(r["providers"][0]); self.assertTrue(validate(r))
    def test_wrong_secret(self):
        r=valid(); r["providers"][0]["secret_name"]="OTHER"; self.assertTrue(validate(r))
    def test_unknown_provider(self):
        r=valid(); r["providers"][0]["name"]="UNKNOWN"; self.assertTrue(validate(r))

if __name__ == "__main__":
    unittest.main()
