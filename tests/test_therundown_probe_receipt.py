import json
import os
import tempfile
import unittest

from therundown_probe_receipt import (
    build_receipt as _raw_build_receipt,
    verify_receipt,
    write_receipt,
)

INTENT_SHA="3"*64

def build_receipt(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_receipt(*args,**kwargs)

class TheRundownProbeReceiptTests(unittest.TestCase):
    def test_missing_execution_intent_checksum_rejected(self):
        with self.assertRaises(ValueError):
            _raw_build_receipt(
                {"status":"HOLD","category":"transport_error"},"x"
            )

    def test_pass_receipt_is_strictly_sample_only(self):
        receipt=build_receipt(
            {
                "status":"PASS",
                "category":"authenticated_zero_datapoint_sample_json",
            },
            "2026-11-04T01:00:00+00:00",
            "a"*40,
            "42",
        )
        self.assertTrue(verify_receipt(receipt))
        self.assertTrue(receipt["sample_only"])
        self.assertTrue(receipt["documented_zero_datapoint_endpoint"])
        self.assertFalse(receipt["model_evidence_allowed"])
        self.assertEqual(
            receipt["endpoint"],
            "https://therundown.io/api/v2/stats/sample",
        )
        rendered=json.dumps(receipt).lower()
        self.assertNotIn("api_key",rendered)
        self.assertNotIn("x-therundown-key",rendered)
        self.assertNotIn("response",rendered)
        self.assertNotIn("headers",rendered)

    def test_mutation_and_extra_field_fail(self):
        receipt=build_receipt(
            {
                "status":"PASS",
                "category":"authenticated_zero_datapoint_sample_json",
            },
            "x",
        )
        receipt["sample_only"]=False
        self.assertFalse(verify_receipt(receipt))
        receipt=build_receipt(
            {"status":"HOLD","category":"transport_error"},"x"
        )
        receipt["raw_headers"]={}
        self.assertFalse(verify_receipt(receipt))

    def test_unknown_category_and_string_detail_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"raw_message"},"x")
        with self.assertRaises(ValueError):
            build_receipt(
                {"status":"HOLD","category":"http_status","detail":"bad"},"x"
            )

    def test_roundtrip(self):
        receipt=build_receipt(
            {"status":"HOLD","category":"transport_error"},"x"
        )
        with tempfile.TemporaryDirectory() as directory:
            path=os.path.join(directory,"receipt.json")
            write_receipt(path,receipt)
            with open(path,encoding="utf-8") as handle:
                loaded=json.load(handle)
        self.assertEqual(loaded,receipt)
        self.assertTrue(verify_receipt(loaded))

if __name__=="__main__":
    unittest.main()
