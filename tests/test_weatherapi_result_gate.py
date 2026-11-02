import unittest
from weatherapi_result_gate import classify

NOW = 1800000000
PAYLOAD = {"location":{"name":"Chicago"},"current":{"last_updated_epoch":NOW-30,"temp_c":14}}

class WeatherApiResultGateTests(unittest.TestCase):
    def test_success_schema_only(self): self.assertEqual(classify(200,PAYLOAD,"Chicago",NOW),"SCHEMA_ACCEPTED_OFFLINE")
    def test_auth(self):
        for status in (401,403): self.assertEqual(classify(status,PAYLOAD,"Chicago",NOW),"HOLD_AUTH")
    def test_rate_limit(self): self.assertEqual(classify(429,PAYLOAD,"Chicago",NOW),"HOLD_RATE_LIMIT")
    def test_redirects(self):
        for status in (301,302,303,307,308): self.assertEqual(classify(status,PAYLOAD,"Chicago",NOW),"HOLD_REDIRECT")
    def test_server_error(self): self.assertEqual(classify(500,PAYLOAD,"Chicago",NOW),"HOLD_HTTP")
    def test_wrong_city(self): self.assertEqual(classify(200,PAYLOAD,"Boston",NOW),"HOLD_DATA")
    def test_bad_payload(self): self.assertEqual(classify(200,{"error":{"code":1002}},"Chicago",NOW),"HOLD_DATA")
    def test_boolean_status(self): self.assertEqual(classify(True,PAYLOAD,"Chicago",NOW),"HOLD_TRANSPORT")

if __name__ == "__main__": unittest.main()
