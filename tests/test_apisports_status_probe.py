import json
import os
import unittest
import urllib.error
from unittest.mock import Mock, patch

import apisports_status_probe
from apisports_status_probe import (
    ACCOUNT_REVIEW_APPROVAL,
    REQUEST_APPROVAL,
    NoRedirectHandler,
    _safe_result,
    probe,
)

PAYLOAD={"errors":[],"results":1,"response":{"requests":{"current":0},"subscription":{"plan":"hidden"}}}
HEADERS={
    "x-ratelimit-requests-limit":"100",
    "x-ratelimit-requests-remaining":"99",
    "x-ratelimit-limit":"10",
    "x-ratelimit-remaining":"9",
}

class FakeResponse:
    status=200
    url="https://v1.american-football.api-sports.io/status"
    headers=HEADERS
    def __init__(self,payload=PAYLOAD,headers=None):
        self.payload=payload
        if headers is not None:
            self.headers=headers
    def read(self,n=-1):
        return json.dumps(self.payload).encode()

class ApiSportsStatusProbeTests(unittest.TestCase):
    def test_account_review_required_before_secret_read(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(probe(REQUEST_APPROVAL,"NO")["category"],"account_review_missing")

    def test_request_approval_required_before_secret_read(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(probe("NO",ACCOUNT_REVIEW_APPROVAL)["category"],"request_approval_missing")

    def test_missing_secret_holds(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL)["category"],"secret_missing")

    def test_mock_success(self):
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            r=probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:FakeResponse())
            self.assertEqual(r["status"],"PASS")
            self.assertNotIn("hidden",repr(r))

    def test_rate_headers_required(self):
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            r=probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:FakeResponse(headers={}))
            self.assertEqual(r["category"],"rate_headers_invalid")

    def test_malformed_json_holds(self):
        class R(FakeResponse):
            def read(self,n=-1): return b"{"
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            self.assertEqual(probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:R())["category"],"malformed_json")

    def test_provider_error_envelope_holds(self):
        bad={"errors":{"token":"hidden"},"response":{"x":1}}
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            r=probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:FakeResponse(bad))
            self.assertEqual(r["category"],"status_contract")
            self.assertNotIn("hidden",repr(r))

    def test_http_statuses_are_sanitized(self):
        cases={401:"auth_denied",403:"entitlement_denied",429:"rate_limited",500:"http_status"}
        for status,category in cases.items():
            def fail(req,timeout,status=status):
                raise urllib.error.HTTPError(req.full_url,status,"provider message",{},None)
            with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
                r=probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=fail)
                self.assertEqual(r["category"],category)
                self.assertNotIn("provider message",repr(r))

    def test_redirect_blocked(self):
        def fail(req,timeout):
            raise urllib.error.HTTPError(req.full_url,302,"Found",{},None)
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            self.assertEqual(probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=fail)["category"],"redirect_blocked")

    def test_endpoint_mismatch_holds(self):
        class R(FakeResponse):
            url="https://example.com/status"
        with patch.dict(os.environ,{"EBT_APISPORTS_API_KEY":"secret"}):
            self.assertEqual(probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:R())["category"],"endpoint_mismatch")

    def test_result_schema_drift_fails_closed(self):
        with self.assertRaises(ValueError): _safe_result("PASS","new_category")
        with self.assertRaises(ValueError): _safe_result("HOLD","http_status","string")

    def test_no_redirect_handler_refuses_follow_up(self):
        self.assertIsNone(NoRedirectHandler().redirect_request(None,None,302,"Found",{},"https://example.com"))

    def test_default_opener_ignores_environment_proxies(self):
        fake=Mock(); fake.open.return_value=object()
        with patch.object(apisports_status_probe.urllib.request,"build_opener",return_value=fake) as build:
            apisports_status_probe._default_open(object(),10)
        handlers=build.call_args.args
        proxy=[h for h in handlers if isinstance(h,apisports_status_probe.urllib.request.ProxyHandler)]
        self.assertEqual(len(proxy),1)
        self.assertEqual(proxy[0].proxies,{})
        self.assertTrue(any(isinstance(h,NoRedirectHandler) for h in handlers))

if __name__=="__main__":
    unittest.main()
