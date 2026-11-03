import json
import os
import tempfile
import unittest

from weatherapi_probe_receipt import build_receipt as _raw_build_receipt, verify_receipt, write_receipt

INTENT_SHA="3"*64

def build_receipt(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_receipt(*args,**kwargs)

class WeatherApiReceiptTests(unittest.TestCase):
    def test_missing_execution_intent_checksum_rejected(self):
        with self.assertRaises(ValueError):
            _raw_build_receipt(
                {"status":"HOLD","category":"transport_error"},"x"
            )

    def test_receipt_contains_only_sanitized_fields(self):
        r = build_receipt(
            {"status":"HOLD","category":"auth_invalid_key","detail":2006},
            "2026-11-02T19:10:00+00:00",
            "abc123",
            "42",
        )
        self.assertEqual(r["provider"], "WeatherAPI")
        self.assertEqual(r["schema_version"],3)
        self.assertEqual(r["execution_intent_sha256"],INTENT_SHA)
        self.assertEqual(r["detail"], 2006)
        self.assertEqual(r["integrity_model"], "sha256-checksum-not-signature")
        self.assertEqual(len(r["receipt_sha256"]), 64)
        self.assertTrue(verify_receipt(r))
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
        self.assertEqual(
            build_receipt(*args)["receipt_sha256"],
            build_receipt(*args)["receipt_sha256"],
        )

    def test_mutation_fails_verification(self):
        r = build_receipt(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T19:10:00+00:00",
            "abc123",
            "42",
        )
        r["status"] = "HOLD"
        self.assertFalse(verify_receipt(r))

    def test_extra_field_fails_verification(self):
        r = build_receipt(
            {"status":"HOLD","category":"transport_error"},
            "x",
        )
        r["raw_provider_message"] = "must never enter receipt"
        self.assertFalse(verify_receipt(r))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"raw_provider_message"}, "x")

    def test_string_detail_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"http_error","detail":"secret"}, "x")

    def test_write_rejects_modified_receipt(self):
        r = build_receipt({"status":"HOLD","category":"transport_error"}, "x")
        r["category"] = "unexpected_error"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                write_receipt(os.path.join(d, "receipt.json"), r)

    def test_write_roundtrip(self):
        receipt = build_receipt({"status":"HOLD","category":"transport_error"}, "x")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "receipt.json")
            write_receipt(path, receipt)
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
        self.assertEqual(loaded, receipt)
        self.assertTrue(verify_receipt(loaded))

if __name__ == "__main__":
    unittest.main()
