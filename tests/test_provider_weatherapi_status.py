"""Offline WeatherAPI classification regression tests; no secrets and no network."""
import unittest

from extensions.weatherapi_status import classify_weatherapi_response as classify


class WeatherAPIStatusTests(unittest.TestCase):
    def test_valid_response_is_reachable_only(self):
        r = classify(200, valid_current_shape=True)
        self.assertEqual(r["connection"], "REACHABLE_ONLY")
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")
        self.assertEqual(r["rights_verified"], "false")
        self.assertEqual(r["feed_verified"], "false")

    def test_no_shape_is_blocked(self):
        self.assertEqual(classify(200)["connection"], "UNEXPECTED_RESPONSE_SHAPE")

    def test_vendor_error_codes(self):
        expected = {
            1002: "MISSING_CREDENTIAL",
            1003: "INVALID_REQUEST",
            1005: "INVALID_REQUEST",
            1006: "LOCATION_NOT_FOUND",
            2006: "INVALID_CREDENTIAL",
            2007: "QUOTA_EXCEEDED",
            2008: "CREDENTIAL_DISABLED",
            2009: "SUBSCRIPTION_DENIED",
            9000: "INVALID_REQUEST",
            9001: "INVALID_REQUEST",
            9999: "PROVIDER_ERROR",
        }
        for code, category in expected.items():
            with self.subTest(code=code):
                self.assertEqual(classify(403, error_code=code)["connection"], category)

    def test_unknown_error_fail_closed(self):
        self.assertEqual(classify(400, error_code=999)["connection"], "UNKNOWN_PROVIDER_ERROR")

    def test_invalid_metadata_fail_closed(self):
        self.assertEqual(classify(200, error_code="2006")["connection"], "INVALID_ERROR_METADATA")
        self.assertEqual(classify(True)["connection"], "UNEXPECTED_HTTP_STATUS")

    def test_http_categories(self):
        self.assertEqual(classify(429)["connection"], "RATE_LIMITED")
        self.assertEqual(classify(503)["connection"], "PROVIDER_ERROR")
        self.assertEqual(classify(401)["connection"], "UNCLASSIFIED_REJECTION")


if __name__ == "__main__":
    unittest.main()
