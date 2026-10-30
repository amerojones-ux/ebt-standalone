"""Credential-free tests for the protected WeatherAPI request plan."""
import unittest

from extensions.weatherapi_request_plan import plan_weatherapi_current

URL = "https://api.weatherapi.com/v1/current.json"


class WeatherRequestPlanTests(unittest.TestCase):
    def test_review_required(self):
        with self.assertRaises(ValueError):
            plan_weatherapi_current(URL)

    def test_canonical_plan_never_authorizes_forecasting(self):
        p = plan_weatherapi_current(URL, reviewed_endpoint=True)
        self.assertEqual((p.host, p.path, p.location),
                         ("api.weatherapi.com", "/v1/current.json", "London"))
        self.assertFalse(p.redirect_allowed)
        self.assertEqual(p.forecast, "HOLD")
        self.assertEqual(p.wager, "NOT APPROVED")
        self.assertNotIn("key", p.__dict__)

    def test_query_credentials_never_accepted(self):
        with self.assertRaises(ValueError):
            plan_weatherapi_current(URL + "?key=EXAMPLE", reviewed_endpoint=True)

    def test_host_confusion_rejected(self):
        for url in ("https://api.weatherapi.com.evil.test/v1/current.json",
                    "https://evil.test@api.weatherapi.com/v1/current.json",
                    "http://api.weatherapi.com/v1/current.json",
                    "https://api.weatherapi.com:444/v1/current.json",
                    "https://api.weatherapi.com/v1/current.json#fragment",
                    "https://api.weatherapi.com/v1/forecast.json"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                plan_weatherapi_current(url, reviewed_endpoint=True)

    def test_location_cannot_be_changed(self):
        with self.assertRaises(ValueError):
            plan_weatherapi_current(URL, location="user", reviewed_endpoint=True)

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValueError):
            plan_weatherapi_current(None, reviewed_endpoint=True)


if __name__ == "__main__":
    unittest.main()
