import unittest
from dataclasses import replace
from provider_capture_integrity import CaptureRecord, canonical_digest, verify_integrity

P={"event_id":"e1","status":"scheduled"}
R=CaptureRecord("example","events","2026-11-01T12:00:00Z","2026-11-01T11:59:00Z",P,canonical_digest(P))
class CaptureIntegrityTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(verify_integrity(R)[0],"PASS")
    def test_missing(self): self.assertEqual(verify_integrity(None)[0],"NOT_TESTED")
    def test_tampered(self): self.assertEqual(verify_integrity(replace(R,payload={"event_id":"e2"}))[0],"FAIL")
    def test_wrong_hash(self): self.assertEqual(verify_integrity(replace(R,sha256="0"*64))[0],"FAIL")
    def test_missing_provider(self): self.assertEqual(verify_integrity(replace(R,provider=""))[0],"FAIL")
    def test_missing_time(self): self.assertEqual(verify_integrity(replace(R,retrieved_at=""))[0],"HOLD")
    def test_order_independent(self): self.assertEqual(canonical_digest({"a":1,"b":2}),canonical_digest({"b":2,"a":1}))
    def test_nan_rejected(self):
        with self.assertRaises(ValueError): canonical_digest({"x":float("nan")})
    def test_none_digest_fails_closed(self):
        self.assertEqual(verify_integrity(replace(R,sha256=None))[0],"FAIL")
    def test_numeric_digest_fails_closed(self):
        self.assertEqual(verify_integrity(replace(R,sha256=123))[0],"FAIL")
if __name__=="__main__": unittest.main()
