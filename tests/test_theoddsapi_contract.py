import unittest
from theoddsapi_contract import validate_quota_headers, validate_sports

SAMPLE = [
    {
        "key": "americanfootball_nfl",
        "group": "American Football",
        "title": "NFL",
        "description": "US Football",
        "active": True,
        "has_outrights": False,
    }
]

class TheOddsApiContractTests(unittest.TestCase):
    def test_valid_sports(self):
        self.assertEqual(validate_sports(SAMPLE), [])

    def test_non_list_rejected(self):
        self.assertTrue(validate_sports({}))

    def test_empty_rejected(self):
        self.assertTrue(validate_sports([]))

    def test_duplicate_key_rejected(self):
        self.assertTrue(validate_sports(SAMPLE + SAMPLE))

    def test_bad_key_rejected(self):
        p=[dict(SAMPLE[0], key="NFL / weird")]
        self.assertTrue(validate_sports(p))

    def test_boolean_types_strict(self):
        p=[dict(SAMPLE[0], active=1)]
        self.assertTrue(validate_sports(p))

    def test_quota_headers_zero_cost(self):
        h={"x-requests-remaining":"500","x-requests-used":"2","x-requests-last":"0"}
        self.assertEqual(validate_quota_headers(h), [])

    def test_nonzero_last_cost_holds(self):
        h={"x-requests-remaining":"499","x-requests-used":"3","x-requests-last":"1"}
        self.assertTrue(validate_quota_headers(h))

    def test_missing_quota_header_holds(self):
        self.assertTrue(validate_quota_headers({}))

if __name__ == "__main__":
    unittest.main()
