import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from weatherapi_live_probe import (
    REQUEST_APPROVAL,
    PLAN_REVIEW_APPROVAL,
    NoRedirectHandler,
    _safe_result,
    probe,
)

NOW = 1800000000
PAYLOAD = {
    "location": {"name": "Chicago"},
    "current": {"last_updated_epoch": NOW - 30, "temp_c": 12.5},
}

class FakeResponse:
    status = 200
    url = "https://api.weatherapi.com/v1/current.json"

    def __init__(self, payload=PAYLOAD):
        self.payload = payload

    def read(self, n=-1):
        return json.dumps(self.payload).encode()

class WeatherApiLiveProbeTests(unittest.TestCase):
    def test_denies_without_plan_review_before_secret_read(self):
        with patch.dict(os.environ, {}, clear=True):
            r = probe(REQUEST_APPROVAL, "NO")
            self.assertEqual(r["category"], "plan_review_missing")

    def test_denies_without_request_approval_before_secret_read(self):
        with patch.dict(os.environ, {}, clear=True):
            r = probe("NO", PLAN_REVIEW_APPROVAL)
            self.assertEqual(r["category"], "request_approval_missing")

    def test_denies_missing_secret_after_both_approvals(self):
        with patch.dict(os.environ, {}, clear=True):
            r = probe(REQUEST_APPROVAL, PLAN_REVIEW_APPROVAL)
            self.assertEqual(r["category"], "secret_missing")

    def test_mock_success(self):
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(),
                now_epoch=NOW,
            )
            self.assertEqual(r["status"], "PASS")

    def test_endpoint_mismatch(self):
        class R(FakeResponse):
            url = "https://example.com/v1/current.json"
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
                now_epoch=NOW,
            )
            self.assertEqual(r["category"], "endpoint_mismatch")

    def test_malformed_json(self):
        class R(FakeResponse):
            def read(self, n=-1):
                return b"{"
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
                now_epoch=NOW,
            )
            self.assertEqual(r["category"], "malformed_json")

    def test_stale_data(self):
        stale = {
            "location": {"name": "Chicago"},
            "current": {"last_updated_epoch": NOW - 7200, "temp_c": 12.5},
        }
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(stale),
                now_epoch=NOW,
            )
            self.assertEqual(r["category"], "data_contract")

    def test_output_object_never_contains_secret(self):
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "SUPERSECRET"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(),
                now_epoch=NOW,
            )
            self.assertNotIn("SUPERSECRET", repr(r))

    def test_boolean_status_holds(self):
        class R(FakeResponse):
            status = True
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
                now_epoch=NOW,
            )
            self.assertEqual(r["status"], "HOLD")

    def test_redirect_http_error_is_blocked(self):
        def redirect(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 302, "Found", {}, None)
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(
                REQUEST_APPROVAL,
                PLAN_REVIEW_APPROVAL,
                opener=redirect,
                now_epoch=NOW,
            )
            self.assertEqual(r["category"], "redirect_blocked")
            self.assertEqual(r["detail"], 302)

    def test_provider_error_codes_are_sanitized(self):
        cases = {
            1002: "auth_missing_key",
            2006: "auth_invalid_key",
            2007: "quota_exceeded",
            2008: "key_disabled",
            2009: "entitlement_denied",
        }
        for code, category in cases.items():
            def fail(req, timeout, code=code):
                body = io.BytesIO(json.dumps({"error":{"code":code,"message":"SECRET MESSAGE"}}).encode())
                raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, body)
            with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
                r = probe(REQUEST_APPROVAL, PLAN_REVIEW_APPROVAL, opener=fail, now_epoch=NOW)
                self.assertEqual(r["category"], category)
                self.assertEqual(r["detail"], code)
                self.assertNotIn("SECRET MESSAGE", repr(r))

    def test_unknown_provider_error_falls_back_to_http_error(self):
        def fail(req, timeout):
            body = io.BytesIO(json.dumps({"error":{"code":9999,"message":"internal"}}).encode())
            raise urllib.error.HTTPError(req.full_url, 500, "Internal", {}, body)
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(REQUEST_APPROVAL, PLAN_REVIEW_APPROVAL, opener=fail, now_epoch=NOW)
            self.assertEqual(r["category"], "http_error")
            self.assertEqual(r["detail"], 9999)

    def test_malformed_error_body_falls_back_to_status(self):
        def fail(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b"{"))
        with patch.dict(os.environ, {"EBT_WEATHER_API_KEY": "test-secret"}):
            r = probe(REQUEST_APPROVAL, PLAN_REVIEW_APPROVAL, opener=fail, now_epoch=NOW)
            self.assertEqual(r["category"], "http_error")
            self.assertEqual(r["detail"], 403)

    def test_result_schema_drift_fails_closed(self):
        with self.assertRaises(ValueError):
            _safe_result("PASS", "not_in_receipt_schema")
        with self.assertRaises(ValueError):
            _safe_result("UNKNOWN", "unexpected_error")
        with self.assertRaises(ValueError):
            _safe_result("HOLD", "http_error", "string-detail")

    def test_no_redirect_handler_refuses_follow_up(self):
        self.assertIsNone(
            NoRedirectHandler().redirect_request(
                None, None, 302, "Found", {}, "https://example.com"
            )
        )

if __name__ == "__main__":
    unittest.main()
