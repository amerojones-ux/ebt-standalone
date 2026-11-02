import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from theoddsapi_live_probe import (
    ACCOUNT_REVIEW_APPROVAL,
    REQUEST_APPROVAL,
    NoRedirectHandler,
    _safe_result,
    probe,
)

SPORTS = [{
    "key": "americanfootball_nfl",
    "group": "American Football",
    "title": "NFL",
    "description": "US Football",
    "active": True,
    "has_outrights": False,
}]
HEADERS = {
    "x-requests-remaining": "500",
    "x-requests-used": "2",
    "x-requests-last": "0",
}

class FakeResponse:
    status = 200
    url = "https://api.the-odds-api.com/v4/sports"
    headers = HEADERS

    def __init__(self, payload=SPORTS, headers=None):
        self.payload = payload
        if headers is not None:
            self.headers = headers

    def read(self, n=-1):
        return json.dumps(self.payload).encode()

class TheOddsApiLiveProbeTests(unittest.TestCase):
    def test_account_review_required_before_secret_read(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                probe(REQUEST_APPROVAL, "NO")["category"],
                "account_review_missing",
            )

    def test_request_approval_required_before_secret_read(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                probe("NO", ACCOUNT_REVIEW_APPROVAL)["category"],
                "request_approval_missing",
            )

    def test_missing_secret_holds(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                probe(REQUEST_APPROVAL, ACCOUNT_REVIEW_APPROVAL)["category"],
                "secret_missing",
            )

    def test_mock_success_requires_zero_credit_headers(self):
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(),
            )
            self.assertEqual(result["status"], "PASS")

    def test_nonzero_usage_cost_holds(self):
        headers = dict(HEADERS, **{"x-requests-last": "1"})
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(headers=headers),
            )
            self.assertEqual(result["category"], "nonzero_usage_cost")

    def test_missing_quota_headers_holds(self):
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(headers={}),
            )
            self.assertEqual(result["category"], "quota_headers_invalid")

    def test_endpoint_mismatch_holds(self):
        class R(FakeResponse):
            url = "https://example.com/v4/sports"
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
            )
            self.assertEqual(result["category"], "endpoint_mismatch")

    def test_malformed_json_holds(self):
        class R(FakeResponse):
            def read(self, n=-1):
                return b"{"
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
            )
            self.assertEqual(result["category"], "malformed_json")

    def test_sports_schema_failure_holds(self):
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(payload=[]),
            )
            self.assertEqual(result["category"], "sports_contract")

    def test_known_provider_error_is_sanitized(self):
        def fail(req, timeout):
            body = io.BytesIO(json.dumps({
                "error_code": "INVALID_KEY",
                "message": "provider message must not escape",
            }).encode())
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, body)
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=fail,
            )
            self.assertEqual(result["category"], "invalid_key")
            self.assertNotIn("provider message", repr(result))

    def test_429_without_body_is_rate_limited(self):
        def fail(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b""))
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=fail,
            )
            self.assertEqual(result["category"], "rate_limited")

    def test_redirect_is_blocked(self):
        def fail(req, timeout):
            raise urllib.error.HTTPError(req.full_url, 302, "Found", {}, None)
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=fail,
            )
            self.assertEqual(result["category"], "redirect_blocked")

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

    def test_boolean_status_holds(self):
        class R(FakeResponse):
            status = True
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "test-secret"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: R(),
            )
            self.assertEqual(result["status"], "HOLD")

    def test_result_never_contains_secret(self):
        with patch.dict(os.environ, {"EBT_THEODDS_API_KEY": "SUPERSECRET"}):
            result = probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req, timeout: FakeResponse(),
            )
            self.assertNotIn("SUPERSECRET", repr(result))

if __name__ == "__main__":
    unittest.main()
