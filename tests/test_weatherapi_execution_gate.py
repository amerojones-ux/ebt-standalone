import unittest
from weatherapi_execution_gate import validate

BASE = {"provider":"WEATHER","secret_name":"EBT_WEATHER_API_KEY","network_enabled":False,"explicit_request_approval":False,"entitlement_verified":False,"quota_verified":False,"cost_verified":False,"forecast_enabled":False,"max_requests":0,"timeout_seconds":10,"allow_redirects":False,"allow_retries":False}
class ExecutionGateTests(unittest.TestCase):
    def test_safe_hold(self): self.assertEqual(validate(BASE),[])
    def test_secret_mapping(self):
        p=dict(BASE,secret_name="WRONG"); self.assertTrue(validate(p))
    def test_network(self):
        p=dict(BASE,network_enabled=True); self.assertTrue(validate(p))
    def test_approval(self):
        p=dict(BASE,explicit_request_approval=True); self.assertTrue(validate(p))
    def test_quota(self):
        p=dict(BASE,quota_verified=True); self.assertTrue(validate(p))
    def test_requests(self):
        p=dict(BASE,max_requests=1); self.assertTrue(validate(p))
    def test_redirect(self):
        p=dict(BASE,allow_redirects=True); self.assertTrue(validate(p))
    def test_forecast(self):
        p=dict(BASE,forecast_enabled=True); self.assertTrue(validate(p))
    def test_unknown_field(self):
        p=dict(BASE,endpoint="example.com"); self.assertTrue(validate(p))
if __name__=="__main__":unittest.main()
