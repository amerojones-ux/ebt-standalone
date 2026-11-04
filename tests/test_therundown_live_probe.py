import json
import os
import unittest
import urllib.error
from unittest.mock import Mock, patch

import therundown_live_probe
from therundown_live_probe import (
    ACCOUNT_REVIEW_APPROVAL,
    REQUEST_APPROVAL,
    NoRedirectHandler,
    _safe_result,
    probe,
)

PAYLOAD={"sample":{"game":"fixed","players":[{"id":1}]}}
URL="https://therundown.io/api/v2/stats/sample"

class FakeResponse:
    status=200
    url=URL
    def __init__(self,payload=PAYLOAD,headers=None):
        self.payload=payload
        self.headers={} if headers is None else headers
    def read(self,n=-1):
        return json.dumps(self.payload).encode()

class TheRundownLiveProbeTests(unittest.TestCase):
    def test_account_review_required_before_secret_read(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(
                probe(REQUEST_APPROVAL,"NO")["category"],
                "account_review_missing",
            )

    def test_request_approval_required_before_secret_read(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(
                probe("NO",ACCOUNT_REVIEW_APPROVAL)["category"],
                "request_approval_missing",
            )

    def test_missing_secret_holds(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(
                probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL)["category"],
                "secret_missing",
            )

    def test_mock_success_without_datapoint_header(self):
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            result=probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req,timeout:FakeResponse(),
            )
        self.assertEqual(result,{
            "status":"PASS",
            "category":"authenticated_zero_datapoint_sample_json",
        })

    def test_explicit_zero_datapoint_header_passes(self):
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            result=probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req,timeout:FakeResponse(headers={"X-Datapoints":"0"}),
            )
        self.assertEqual(result["status"],"PASS")

    def test_nonzero_datapoint_header_holds(self):
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            result=probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req,timeout:FakeResponse(headers={"X-Datapoints":"2"}),
            )
        self.assertEqual(result["category"],"unexpected_datapoint_charge")
        self.assertEqual(result["detail"],2)

    def test_invalid_datapoint_header_holds(self):
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            result=probe(
                REQUEST_APPROVAL,
                ACCOUNT_REVIEW_APPROVAL,
                opener=lambda req,timeout:FakeResponse(headers={"X-Datapoints":"bad"}),
            )
        self.assertEqual(result["category"],"datapoint_header_invalid")

    def test_malformed_or_empty_json_holds(self):
        class Bad(FakeResponse):
            def read(self,n=-1): return b"{"
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            self.assertEqual(
                probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:Bad())["category"],
                "malformed_json",
            )
            self.assertEqual(
                probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:FakeResponse({}))["category"],
                "empty_sample",
            )

    def test_http_statuses_are_sanitized(self):
        cases={
            401:"auth_denied",
            403:"entitlement_denied",
            429:"rate_limited",
            500:"http_status",
        }
        for status,category in cases.items():
            def fail(req,timeout,status=status):
                raise urllib.error.HTTPError(
                    req.full_url,status,"provider secret message",{},None
                )
            with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
                result=probe(
                    REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=fail
                )
            self.assertEqual(result["category"],category)
            self.assertNotIn("provider secret message",repr(result))

    def test_redirect_and_endpoint_mismatch_hold(self):
        def redirect(req,timeout):
            raise urllib.error.HTTPError(req.full_url,302,"Found",{},None)
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            self.assertEqual(
                probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=redirect)["category"],
                "redirect_blocked",
            )
            bad=FakeResponse()
            bad.url="https://example.com/api/v2/stats/sample"
            self.assertEqual(
                probe(REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=lambda req,timeout:bad)["category"],
                "endpoint_mismatch",
            )

    def test_request_is_exact_and_key_is_header_only(self):
        captured={}
        def inspect(req,timeout):
            captured["url"]=req.full_url
            captured["method"]=req.get_method()
            captured["headers"]={k.lower():v for k,v in req.header_items()}
            return FakeResponse()
        with patch.dict(os.environ,{"EBT_THERUNDOWN_API_KEY":"secret"}):
            result=probe(
                REQUEST_APPROVAL,ACCOUNT_REVIEW_APPROVAL,opener=inspect
            )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(captured["url"],URL)
        self.assertEqual(captured["method"],"GET")
        self.assertEqual(
            set(captured["headers"]),
            {"accept","x-therundown-key"},
        )
        self.assertEqual(captured["headers"]["x-therundown-key"],"secret")
        self.assertNotIn("secret",captured["url"])

    def test_result_schema_drift_fails_closed(self):
        with self.assertRaises(ValueError):
            _safe_result("PASS","new_category")
        with self.assertRaises(ValueError):
            _safe_result("HOLD","http_status","string")

    def test_default_opener_disables_proxies_redirects_and_default_headers(self):
        fake=Mock()
        fake.open.return_value=object()
        fake.addheaders=[("User-agent","unsafe")]
        with patch.object(
            therundown_live_probe.urllib.request,
            "build_opener",
            return_value=fake,
        ) as build:
            therundown_live_probe._default_open(object(),10)
        handlers=build.call_args.args
        proxy=[
            h for h in handlers
            if isinstance(h,therundown_live_probe.urllib.request.ProxyHandler)
        ]
        self.assertEqual(len(proxy),1)
        self.assertEqual(proxy[0].proxies,{})
        self.assertTrue(any(isinstance(h,NoRedirectHandler) for h in handlers))
        self.assertEqual(fake.addheaders,[])

if __name__=="__main__":
    unittest.main()
