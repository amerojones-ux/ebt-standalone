import unittest
from provider_endpoint_policy import EndpointPolicy, verify_url
P=EndpointPolicy("WeatherAPI","api.weatherapi.com","/v1")
class URLPolicyTests(unittest.TestCase):
    def check(self,url,expected): self.assertEqual(verify_url(P,url)[0],expected)
    def test_good(self): self.check("https://api.weatherapi.com/v1/current.json","PASS")
    def test_http(self): self.check("http://api.weatherapi.com/v1/current.json","FAIL")
    def test_other_host(self): self.check("https://evil.example/v1/current.json","FAIL")
    def test_subdomain(self): self.check("https://api.weatherapi.com.evil.example/v1","FAIL")
    def test_credentials(self): self.check("https://user:pass@api.weatherapi.com/v1","FAIL")
    def test_port(self): self.check("https://api.weatherapi.com:8080/v1","FAIL")
    def test_path(self): self.check("https://api.weatherapi.com/admin","FAIL")
    def test_path_prefix_confusion(self): self.check("https://api.weatherapi.com/v11","FAIL")
    def test_fragment(self): self.check("https://api.weatherapi.com/v1#secret","FAIL")
    def test_invalid(self): self.check("not-a-url","FAIL")
if __name__=="__main__": unittest.main()
