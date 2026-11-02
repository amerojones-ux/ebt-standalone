import unittest
from unittest.mock import patch
from provider_endpoint_policy import EndpointPolicy
from provider_live_gate import LivePlan,validate_plan,execute
P=EndpointPolicy("WeatherAPI","api.weatherapi.com","/v1")
PLAN=LivePlan("WeatherAPI",P,"https://api.weatherapi.com/v1/current.json","X-API-Key","contract-1","approval-1")
C=frozenset({"contract-1"})
A=frozenset({"approval-1"})
class LiveGateTests(unittest.TestCase):
    def test_approved_plan(self): self.assertEqual(validate_plan(PLAN,approved_contracts=C,approved_approvals=A)[0],"PASS")
    def test_no_approval(self): self.assertEqual(validate_plan(PLAN,approved_contracts=C,approved_approvals=frozenset())[0],"HOLD")
    def test_no_contract(self): self.assertEqual(validate_plan(PLAN,approved_contracts=frozenset(),approved_approvals=A)[0],"HOLD")
    def test_no_credential(self): self.assertEqual(execute(PLAN,credential="",approved_contracts=C,approved_approvals=A).status,"HOLD")
    def test_no_network_when_unapproved(self):
        with patch("provider_live_gate.collect") as mocked:
            self.assertEqual(execute(PLAN,credential="dummy",approved_contracts=C,approved_approvals=frozenset()).status,"HOLD")
            mocked.assert_not_called()
    def test_request_budget(self):
        from dataclasses import replace
        self.assertEqual(validate_plan(replace(PLAN,max_requests=2),approved_contracts=C,approved_approvals=A)[0],"FAIL")
    def test_invalid_provider(self):
        from dataclasses import replace
        self.assertEqual(validate_plan(replace(PLAN,provider="Unknown"),approved_contracts=C,approved_approvals=A)[0],"FAIL")
if __name__=="__main__": unittest.main()
