import unittest
from rapidapi_routing_contract import validate_plan, can_prepare_live_probe, can_execute_request

PLAN = {
    "provider":"RapidAPI",
    "secret_name":"EBT_RAPIDAPI_API_KEY",
    "key_header":"X-RapidAPI-Key",
    "host_header":"X-RapidAPI-Host",
    "api_product":"Example Sports Provider",
    "rapidapi_host":"example-sports.p.rapidapi.com",
    "pricing_type":"FREEMIUM",
    "plan_name":"BASIC",
    "billing_object":"Requests",
    "subscription_verified":True,
    "quota_reviewed":True,
    "overage_reviewed":True,
    "endpoint_reviewed":True,
    "network_enabled":False,
    "request_count":0,
    "forecast_enabled":False,
}

class RapidApiRoutingContractTests(unittest.TestCase):
    def test_fully_reviewed_plan_can_prepare_but_not_execute(self):
        self.assertEqual(validate_plan(PLAN), [])
        self.assertTrue(can_prepare_live_probe(PLAN))
        self.assertFalse(can_execute_request(PLAN))

    def test_literal_all_is_ambiguous(self):
        p=dict(PLAN,api_product="all")
        self.assertTrue(validate_plan(p))

    def test_missing_host_holds(self):
        p=dict(PLAN,rapidapi_host="")
        self.assertTrue(validate_plan(p))

    def test_bad_host_holds(self):
        p=dict(PLAN,rapidapi_host="https://example-sports.p.rapidapi.com/path")
        self.assertTrue(validate_plan(p))

    def test_unknown_pricing_holds(self):
        p=dict(PLAN,pricing_type="UNKNOWN")
        self.assertTrue(validate_plan(p))

    def test_missing_plan_name_holds(self):
        p=dict(PLAN,plan_name="")
        self.assertTrue(validate_plan(p))

    def test_each_review_gate_is_required(self):
        for key in ("subscription_verified","quota_reviewed","overage_reviewed","endpoint_reviewed"):
            with self.subTest(key=key):
                p=dict(PLAN); p[key]=False
                self.assertTrue(validate_plan(p))

    def test_network_enable_holds(self):
        p=dict(PLAN,network_enabled=True)
        self.assertTrue(validate_plan(p))

    def test_nonzero_request_count_holds(self):
        p=dict(PLAN,request_count=1)
        self.assertTrue(validate_plan(p))

    def test_wrong_headers_hold(self):
        p=dict(PLAN,key_header="Authorization",host_header="Host")
        self.assertTrue(validate_plan(p))

if __name__=="__main__":
    unittest.main()
