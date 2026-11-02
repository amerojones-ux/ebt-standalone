import unittest
from unittest.mock import patch
from secure_provider_collector import collect, CollectorConfig
from provider_endpoint_policy import EndpointPolicy
P=EndpointPolicy("WeatherAPI","api.weatherapi.com","/v1")
URL="https://api.weatherapi.com/v1/current.json"
class CollectorTests(unittest.TestCase):
    def test_invalid_url_no_network(self):
        with patch("secure_provider_collector.build_opener") as op:
            r=collect(P,"http://api.weatherapi.com/v1/current.json")
            self.assertEqual(r.status,"FAIL")
            op.assert_not_called()
    def test_unapproved_host_no_network(self):
        with patch("secure_provider_collector.build_opener") as op:
            self.assertEqual(collect(P,"https://evil.example/v1/current.json").status,"FAIL")
            op.assert_not_called()
    def test_timeout_limit(self):
        self.assertEqual(collect(P,URL,config=CollectorConfig(timeout_seconds=60)).status,"FAIL")
    def test_body_limit(self):
        self.assertEqual(collect(P,URL,config=CollectorConfig(max_body_bytes=2000000)).status,"FAIL")
    def test_forbidden_header(self):
        self.assertEqual(collect(P,URL,headers={"Cookie":"secret"}).status,"FAIL")
    def test_redirect_rejected(self):
        from secure_provider_collector import RejectRedirect
        self.assertIsNone(RejectRedirect().redirect_request(None,None,302,"Moved",{},"https://evil.example"))
if __name__=="__main__": unittest.main()
