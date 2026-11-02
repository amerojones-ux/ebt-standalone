import unittest
from provider_endpoint_policy import EndpointPolicy, verify_url
from secure_provider_collector import collect
P=EndpointPolicy("WeatherAPI","api.weatherapi.com","/v1")
U="https://api.weatherapi.com/v1/current.json"
class AdversarialSecurityTests(unittest.TestCase):
    def test_query_forbidden(self): self.assertEqual(verify_url(P,U+"?key=secret")[0],"FAIL")
    def test_encoded_parent(self): self.assertEqual(verify_url(P,"https://api.weatherapi.com/v1/%2e%2e/admin")[0],"FAIL")
    def test_double_encoded_parent(self): self.assertEqual(verify_url(P,"https://api.weatherapi.com/v1/%252e%252e/admin")[0],"FAIL")
    def test_backslash(self): self.assertEqual(verify_url(P,"https://api.weatherapi.com/v1/%5cadmin")[0],"FAIL")
    def test_crlf_url(self): self.assertEqual(verify_url(P,U+"\r\n")[0],"FAIL")
    def test_header_injection(self): self.assertEqual(collect(P,U,headers={"Authorization":"Bearer x\r\nInjected: yes"}).status,"FAIL")
    def test_unapproved_header(self): self.assertEqual(collect(P,U,headers={"X-Forwarded-Host":"evil.example"}).status,"FAIL")
    def test_api_key_header_allowed_validation_only(self):
        from unittest.mock import patch
        with patch("secure_provider_collector.build_opener") as opener:
            opener.return_value.open.side_effect = OSError("synthetic transport failure")
            self.assertEqual(collect(P,U,headers={"X-API-Key":"dummy"}).status,"HOLD")
    def test_opener_initialization_failure(self):
        from unittest.mock import patch
        with patch("secure_provider_collector.build_opener", side_effect=OSError("synthetic initialization failure")):
            self.assertEqual(collect(P,U).status,"HOLD")
if __name__=="__main__": unittest.main()
