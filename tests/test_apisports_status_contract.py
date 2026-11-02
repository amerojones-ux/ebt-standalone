import unittest

from apisports_status_contract import validate_rate_headers, validate_status_payload

HEADERS = {
    "x-ratelimit-requests-limit": "100",
    "x-ratelimit-requests-remaining": "99",
    "x-ratelimit-limit": "10",
    "x-ratelimit-remaining": "9",
}

class ApiSportsStatusContractTests(unittest.TestCase):
    def test_valid_headers(self):
        self.assertEqual(validate_rate_headers(HEADERS), [])

    def test_missing_headers_hold(self):
        self.assertTrue(validate_rate_headers({}))

    def test_negative_header_holds(self):
        h=dict(HEADERS, **{"x-ratelimit-requests-remaining":"-1"})
        self.assertTrue(validate_rate_headers(h))

    def test_daily_remaining_cannot_exceed_limit(self):
        h=dict(HEADERS, **{"x-ratelimit-requests-remaining":"101"})
        self.assertTrue(validate_rate_headers(h))

    def test_minute_remaining_cannot_exceed_limit(self):
        h=dict(HEADERS, **{"x-ratelimit-remaining":"11"})
        self.assertTrue(validate_rate_headers(h))

    def test_valid_minimal_status_payload(self):
        payload={"errors":[],"results":1,"response":{"requests":{"current":0}}}
        self.assertEqual(validate_status_payload(payload), [])

    def test_non_object_payload_holds(self):
        self.assertTrue(validate_status_payload([]))

    def test_provider_errors_hold(self):
        payload={"errors":{"token":"invalid"},"response":{"x":1}}
        self.assertTrue(validate_status_payload(payload))

    def test_empty_response_holds(self):
        self.assertTrue(validate_status_payload({"errors":[],"response":{}}))

    def test_bad_results_type_holds(self):
        self.assertTrue(validate_status_payload({"response":{"x":1},"results":True}))

if __name__ == "__main__":
    unittest.main()
