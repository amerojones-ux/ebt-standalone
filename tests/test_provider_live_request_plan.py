import unittest
import urllib.parse
import urllib.request

from provider_live_request_plan import (
    PLANS,
    build_request,
    public_plan,
    validate_request,
    validate_response_url,
)

class ProviderLiveRequestPlanTests(unittest.TestCase):
    def test_weatherapi_exact_request_has_only_key_and_q(self):
        req=build_request("WeatherAPI","SECRET")
        parsed=urllib.parse.urlsplit(req.full_url)
        query=urllib.parse.parse_qs(parsed.query,keep_blank_values=True)
        self.assertEqual(set(query),{"key","q"})
        self.assertEqual(query["q"],["Chicago"])
        self.assertEqual(query["key"],["SECRET"])
        self.assertNotIn("aqi",query)
        self.assertEqual(validate_request(req,"WeatherAPI"),[])

    def test_theoddsapi_exact_request_has_only_api_key(self):
        req=build_request("The Odds API","SECRET")
        parsed=urllib.parse.urlsplit(req.full_url)
        query=urllib.parse.parse_qs(parsed.query,keep_blank_values=True)
        self.assertEqual(query,{"apiKey":["SECRET"]})
        self.assertEqual(validate_request(req,"The Odds API"),[])

    def test_apisports_exact_request_has_no_query_and_one_header(self):
        req=build_request("API-Sports","SECRET")
        parsed=urllib.parse.urlsplit(req.full_url)
        self.assertEqual(parsed.query,"")
        headers={k.lower():v for k,v in req.header_items()}
        self.assertEqual(headers,{"x-apisports-key":"SECRET"})
        self.assertEqual(validate_request(req,"API-Sports"),[])

    def test_all_plans_are_one_shot_no_redirect_no_retry(self):
        for provider,plan in PLANS.items():
            with self.subTest(provider=provider):
                self.assertEqual(plan["method"],"GET")
                self.assertEqual(plan["timeout_seconds"],10)
                self.assertEqual(plan["max_requests"],1)
                self.assertIs(plan["allow_redirects"],False)
                self.assertEqual(plan["retries"],0)

    def test_public_plan_never_contains_credential_value(self):
        for provider in PLANS:
            plan=public_plan(provider)
            self.assertNotIn("SECRET",repr(plan))
            self.assertNotIn("credential",repr(plan).lower())

    def test_extra_weather_query_key_rejected(self):
        req=urllib.request.Request(
            "https://api.weatherapi.com/v1/current.json?key=x&q=Chicago&aqi=no",
            method="GET",
            headers={
                "Accept":"application/json",
                "User-Agent":"EBT-Black-Diamond/WeatherAPI-Auth-Probe",
            },
        )
        self.assertTrue(validate_request(req,"WeatherAPI"))

    def test_duplicate_query_key_rejected(self):
        req=urllib.request.Request(
            "https://api.the-odds-api.com/v4/sports?apiKey=x&apiKey=y",
            method="GET",
            headers={
                "Accept":"application/json",
                "User-Agent":"EBT-Black-Diamond/TheOddsAPI-Auth-Probe",
            },
        )
        self.assertTrue(validate_request(req,"The Odds API"))

    def test_wrong_fixed_location_rejected(self):
        req=urllib.request.Request(
            "https://api.weatherapi.com/v1/current.json?key=x&q=New%20York",
            method="GET",
            headers={
                "Accept":"application/json",
                "User-Agent":"EBT-Black-Diamond/WeatherAPI-Auth-Probe",
            },
        )
        self.assertTrue(validate_request(req,"WeatherAPI"))

    def test_extra_header_rejected(self):
        req=build_request("The Odds API","SECRET")
        req.add_header("X-Extra","1")
        self.assertTrue(validate_request(req,"The Odds API"))

    def test_wrong_method_rejected(self):
        req=urllib.request.Request(
            "https://v1.american-football.api-sports.io/status",
            method="POST",
            headers={"x-apisports-key":"x"},
        )
        self.assertTrue(validate_request(req,"API-Sports"))

    def test_body_rejected(self):
        req=urllib.request.Request(
            "https://v1.american-football.api-sports.io/status",
            data=b"x",
            method="GET",
            headers={"x-apisports-key":"x"},
        )
        self.assertTrue(validate_request(req,"API-Sports"))

    def test_userinfo_port_fragment_rejected(self):
        cases=[
            "https://user@api.weatherapi.com/v1/current.json?key=x&q=Chicago",
            "https://api.weatherapi.com:443/v1/current.json?key=x&q=Chicago",
            "https://api.weatherapi.com/v1/current.json?key=x&q=Chicago#frag",
        ]
        for url in cases:
            with self.subTest(url=url):
                req=urllib.request.Request(
                    url,
                    method="GET",
                    headers={
                        "Accept":"application/json",
                        "User-Agent":"EBT-Black-Diamond/WeatherAPI-Auth-Probe",
                    },
                )
                self.assertTrue(validate_request(req,"WeatherAPI"))

    def test_response_url_rejects_userinfo_port_fragment_and_wrong_host(self):
        cases=[
            "https://user@api.the-odds-api.com/v4/sports",
            "https://api.the-odds-api.com:443/v4/sports",
            "https://api.the-odds-api.com/v4/sports#frag",
            "https://evil.example/v4/sports",
        ]
        for url in cases:
            with self.subTest(url=url):
                self.assertTrue(validate_response_url(url,"The Odds API"))

    def test_response_url_accepts_exact_endpoint_with_or_without_query(self):
        self.assertEqual(
            validate_response_url(
                "https://api.weatherapi.com/v1/current.json?key=x&q=Chicago",
                "WeatherAPI",
            ),
            [],
        )
        self.assertEqual(
            validate_response_url(
                "https://api.weatherapi.com/v1/current.json",
                "WeatherAPI",
            ),
            [],
        )

    def test_unsupported_provider_fails_closed(self):
        with self.assertRaises(ValueError):
            build_request("Unknown","x")
        with self.assertRaises(ValueError):
            public_plan("Unknown")

if __name__=="__main__":
    unittest.main()
