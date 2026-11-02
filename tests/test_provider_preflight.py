import unittest
from provider_preflight import validate, PROVIDERS

def plan():
    return {"mode":"offline","network_enabled":False,"forecast_enabled":False,
            "providers":[{"name":n,"secret_name":s,"request_count":0} for n,s in PROVIDERS.items()]}

class PreflightTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(plan()), [])
    def test_live_mode_denied(self):
        p=plan(); p["mode"]="live"; self.assertTrue(validate(p))
    def test_network_denied(self):
        p=plan(); p["network_enabled"]=True; self.assertTrue(validate(p))
    def test_forecast_denied(self):
        p=plan(); p["forecast_enabled"]=True; self.assertTrue(validate(p))
    def test_missing_provider_denied(self):
        p=plan(); p["providers"].pop(); self.assertTrue(validate(p))
    def test_duplicate_denied(self):
        p=plan(); p["providers"][1]=p["providers"][0]; self.assertTrue(validate(p))
    def test_wrong_secret_denied(self):
        p=plan(); p["providers"][0]["secret_name"]="WRONG"; self.assertTrue(validate(p))
    def test_requests_denied(self):
        p=plan(); p["providers"][0]["request_count"]=1; self.assertTrue(validate(p))

if __name__ == "__main__":
    unittest.main()
