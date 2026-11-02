import json
import os
import tempfile
import unittest

from theoddsapi_probe_receipt import build_receipt, write_receipt

class TheOddsApiReceiptTests(unittest.TestCase):
    def test_receipt_is_sanitized(self):
        receipt = build_receipt(
            {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
            "2026-11-02T19:20:00+00:00",
            "abc",
            "42",
        )
        rendered = json.dumps(receipt)
        self.assertEqual(receipt["zero_usage_credit_required"], True)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)
        self.assertNotIn("apiKey", rendered)
        self.assertNotIn("secret", rendered.lower())

    def test_hash_is_deterministic(self):
        args = (
            {"status":"HOLD","category":"invalid_key"},
            "2026-11-02T19:20:00+00:00",
            "abc",
            "42",
        )
        self.assertEqual(
            build_receipt(*args)["receipt_sha256"],
            build_receipt(*args)["receipt_sha256"],
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"raw_message"}, "x")

    def test_string_detail_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"http_error","detail":"bad"}, "x")

    def test_roundtrip(self):
        receipt = build_receipt({"status":"HOLD","category":"transport_error"}, "x")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "receipt.json")
            write_receipt(path, receipt)
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
        self.assertEqual(loaded, receipt)

if __name__ == "__main__":
    unittest.main()
