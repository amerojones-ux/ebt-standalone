import json
import os
import unittest
from unittest.mock import patch

import apisports_status_probe
import theoddsapi_live_probe
import weatherapi_live_probe
import therundown_live_probe
from provider_live_request_plan import get_plan, validate_request

NOW=1800000000

class Response:
    status=200
    def __init__(self,url,payload,headers=None):
        self.url=url
        self.payload=payload
        self.headers={} if headers is None else headers
    def read(self,n=-1):
        return json.dumps(self.payload).encode()

class CountingOpener:
    def __init__(self,response,provider):
        self.response=response
        self.provider=provider
        self.calls=[]
    def __call__(self,request,timeout):
        self.calls.append((request,timeout))
        errors=validate_request(request,self.provider)
        if errors:
            raise AssertionError(errors)
        return self.response

class LiveProbeRequestPlanIntegrationTests(unittest.TestCase):
    def test_weatherapi_probe_uses_exact_plan_once(self):
        response=Response(
            "https://api.weatherapi.com/v1/current.json",
            {
                "location":{"name":"Chicago"},
                "current":{"last_updated_epoch":NOW-30,"temp_c":12.5},
            },
        )
        opener=CountingOpener(response,"WeatherAPI")
        with patch.dict(
            os.environ,{"EBT_WEATHER_API_KEY":"test-secret"},clear=True
        ):
            result=weatherapi_live_probe.probe(
                weatherapi_live_probe.REQUEST_APPROVAL,
                weatherapi_live_probe.PLAN_REVIEW_APPROVAL,
                opener=opener,
                now_epoch=NOW,
            )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(len(opener.calls),1)
        request,timeout=opener.calls[0]
        self.assertEqual(timeout,get_plan("WeatherAPI")["timeout_seconds"])
        self.assertNotIn("aqi=",request.full_url)

    def test_theoddsapi_probe_uses_exact_plan_once(self):
        response=Response(
            "https://api.the-odds-api.com/v4/sports",
            [{
                "key":"americanfootball_nfl",
                "group":"American Football",
                "title":"NFL",
                "active":True,
                "has_outrights":False,
            }],
            {
                "x-requests-remaining":"500",
                "x-requests-used":"2",
                "x-requests-last":"0",
            },
        )
        opener=CountingOpener(response,"The Odds API")
        with patch.dict(
            os.environ,{"EBT_THEODDS_API_KEY":"test-secret"},clear=True
        ):
            result=theoddsapi_live_probe.probe(
                theoddsapi_live_probe.REQUEST_APPROVAL,
                theoddsapi_live_probe.ACCOUNT_REVIEW_APPROVAL,
                opener=opener,
            )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(len(opener.calls),1)
        request,timeout=opener.calls[0]
        self.assertEqual(timeout,get_plan("The Odds API")["timeout_seconds"])

    def test_therundown_probe_uses_exact_plan_once(self):
        response=Response(
            "https://therundown.io/api/v2/stats/sample",
            {"sample":{"fixed":True}},
            {"x-datapoints":"0"},
        )
        opener=CountingOpener(response,"TheRundown")
        with patch.dict(
            os.environ,{"EBT_THERUNDOWN_API_KEY":"test-secret"},clear=True
        ):
            result=therundown_live_probe.probe(
                therundown_live_probe.REQUEST_APPROVAL,
                therundown_live_probe.ACCOUNT_REVIEW_APPROVAL,
                opener=opener,
            )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(len(opener.calls),1)
        request,timeout=opener.calls[0]
        self.assertEqual(timeout,get_plan("TheRundown")["timeout_seconds"])
        self.assertEqual(
            request.full_url,
            "https://therundown.io/api/v2/stats/sample",
        )

    def test_apisports_probe_uses_exact_plan_once(self):
        response=Response(
            "https://v1.american-football.api-sports.io/status",
            {
                "errors":[],
                "results":1,
                "response":{"requests":{"current":0}},
            },
            {
                "x-ratelimit-requests-limit":"100",
                "x-ratelimit-requests-remaining":"99",
                "x-ratelimit-limit":"10",
                "x-ratelimit-remaining":"9",
            },
        )
        opener=CountingOpener(response,"API-Sports")
        with patch.dict(
            os.environ,{"EBT_APISPORTS_API_KEY":"test-secret"},clear=True
        ):
            result=apisports_status_probe.probe(
                apisports_status_probe.REQUEST_APPROVAL,
                apisports_status_probe.ACCOUNT_REVIEW_APPROVAL,
                opener=opener,
            )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(len(opener.calls),1)
        request,timeout=opener.calls[0]
        self.assertEqual(timeout,get_plan("API-Sports")["timeout_seconds"])

    def test_secret_missing_never_calls_opener(self):
        class FailOpener:
            def __call__(self,request,timeout):
                raise AssertionError("opener must not be called")
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(
                weatherapi_live_probe.probe(
                    weatherapi_live_probe.REQUEST_APPROVAL,
                    weatherapi_live_probe.PLAN_REVIEW_APPROVAL,
                    opener=FailOpener(),
                    now_epoch=NOW,
                )["category"],
                "secret_missing",
            )

if __name__=="__main__":
    unittest.main()
