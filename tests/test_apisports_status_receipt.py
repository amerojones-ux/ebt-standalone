import json
import os
import tempfile
import unittest

from apisports_status_receipt import build_receipt as _raw_build_receipt, verify_receipt, write_receipt

INTENT_SHA="3"*64

def build_receipt(*args,**kwargs):
    kwargs.setdefault("execution_intent_sha256",INTENT_SHA)
    return _raw_build_receipt(*args,**kwargs)

class ApiSportsStatusReceiptTests(unittest.TestCase):
    def test_missing_execution_intent_checksum_rejected(self):
        with self.assertRaises(ValueError):
            _raw_build_receipt(
                {"status":"HOLD","category":"transport_error"},"x"
            )

    def test_receipt_excludes_account_and_quota_values(self):
        r=build_receipt(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:00:00+00:00","abc","42"
        )
        rendered=json.dumps(r).lower()
        self.assertTrue(verify_receipt(r))
        self.assertEqual(r["schema_version"],2)
        self.assertEqual(r["execution_intent_sha256"],INTENT_SHA)
        self.assertNotIn("subscription",rendered)
        self.assertNotIn("remaining",rendered)
        self.assertNotIn("api_key",rendered)
        self.assertEqual(r["integrity_model"],"sha256-checksum-not-signature")

    def test_mutation_fails(self):
        r=build_receipt({"status":"HOLD","category":"transport_error"},"x")
        r["status"]="PASS"
        self.assertFalse(verify_receipt(r))

    def test_extra_field_fails(self):
        r=build_receipt({"status":"HOLD","category":"transport_error"},"x")
        r["quota_balance"]=100
        self.assertFalse(verify_receipt(r))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            build_receipt({"status":"HOLD","category":"raw_account_data"},"x")

    def test_roundtrip(self):
        r=build_receipt({"status":"HOLD","category":"transport_error"},"x")
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,"r.json")
            write_receipt(path,r)
            with open(path,encoding="utf-8") as h:
                loaded=json.load(h)
        self.assertTrue(verify_receipt(loaded))
        self.assertEqual(loaded,r)

if __name__=="__main__":
    unittest.main()
