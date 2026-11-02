import io
import json
import os
import unittest
from unittest.mock import patch

from weatherapi_live_probe import APPROVAL, probe

NOW = 1800000000
PAYLOAD = {"location":{"name":"Chicago"},"current":{"last_updated_epoch":NOW-30,"temp_c":12.5}}

class FakeResponse:
    status=200
    url="https://api.weatherapi.com/v1/current.json"
    def __init__(self, payload=PAYLOAD):
        self.payload=payload
    def read(self, n=-1):
        return json.dumps(self.payload).encode()

class WeatherApiLiveProbeTests(unittest.TestCase):
    def test_denies_without_exact_approval_before_secret_read(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe("NO")["category"], "approval_missing")
    def test_denies_missing_secret(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe(APPROVAL)["category"], "secret_missing")
    def test_mock_success(self):
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"test-secret"}):
            r=probe(APPROVAL, opener=lambda req,timeout: FakeResponse(), now_epoch=NOW)
            self.assertEqual(r["status"], "PASS")
    def test_endpoint_mismatch(self):
        class R(FakeResponse): url="https://example.com/v1/current.json"
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"test-secret"}):
            self.assertEqual(probe(APPROVAL, opener=lambda req,timeout:R(), now_epoch=NOW)["category"],"redirect_or_endpoint_mismatch")
    def test_malformed_json(self):
        class R(FakeResponse):
            def read(self,n=-1): return b"{"
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"test-secret"}):
            self.assertEqual(probe(APPROVAL, opener=lambda req,timeout:R(), now_epoch=NOW)["category"],"malformed_json")
    def test_stale_data(self):
        stale={"location":{"name":"Chicago"},"current":{"last_updated_epoch":NOW-7200,"temp_c":12.5}}
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"test-secret"}):
            self.assertEqual(probe(APPROVAL, opener=lambda req,timeout:FakeResponse(stale), now_epoch=NOW)["category"],"data_contract")
    def test_output_object_never_contains_secret(self):
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"SUPERSECRET"}):
            r=probe(APPROVAL, opener=lambda req,timeout:FakeResponse(), now_epoch=NOW)
            self.assertNotIn("SUPERSECRET", repr(r))
    def test_boolean_or_bad_status_holds(self):
        class R(FakeResponse): status=True
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY":"test-secret"}):
            self.assertEqual(probe(APPROVAL, opener=lambda req,timeout:R(), now_epoch=NOW)["status"],"HOLD")

if __name__ == "__main__": unittest.main()
