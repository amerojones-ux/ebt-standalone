import json
import os
import tempfile
import unittest

from weatherapi_probe_receipt import build_receipt, write_receipt

class WeatherApiReceiptTests(unittest.TestCase):
    def test_receipt_contains_only_sanitized_fields(self):
        r = build_receipt(
            {"status":"HOLD","category":"auth_invalid_key","detail":2006},
            "2026-11-02T19:10:00+00:00",
            "abc123",
            "42",
        )
        self.assertEqual(r["provider"], "WeatherAPI")
        self.assertEqual(r["detail"], 2006)
        self.assertEqual(len(r["receipt_sha256"]), 64)
        rendered = json.dumps(r)
        self.assertNotIn("api_key", rendered.lower())
        self.assertNotIn("message", rendered.lower())

    def test_hash_is_deterministic(self):
        args = (
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T19:10:00+00:00",
            "abc123",
            "42",
        )
        self.assertEqual(build_receipt(*args)["receipt_sha256"], build_receipt(*args)["receipt_sha256"])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"raw_provider_message"}, "x")

    def test_string_detail_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"http_error","detail":"secret"}, "x")

    def test_write_roundtrip(self):
        receipt = build_receipt({"status":"HOLD","category":"transport_error"}, "x")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "receipt.json")
            write_receipt(path, receipt)
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
        self.assertEqual(loaded, receipt)

if __name__ == "__main__":
    unittest.main()
