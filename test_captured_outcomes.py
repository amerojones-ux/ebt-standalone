import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from ebt_captured_outcomes import reconcile_captured_outcomes
from ebt_certification import CertificationHold

class CapturedOutcomeTests(unittest.TestCase):
    def test_matching_content_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            final={"event_id":"g","player_id":"p","market":"points",
                   "status":"final","value":12,
                   "reported_at":"2026-10-29T02:00:00Z","capture_id":"official"}
            body=json.dumps({k:v for k,v in final.items() if k!="capture_id"}).encode()
            Path(d,"capture.json").write_bytes(body)
            index={"official":{"sha256":hashlib.sha256(body).hexdigest(),
                               "url":"https://official.nba.com/fixture",
                               "retrieved_at":"2026-10-29T02:01:00Z",
                               "raw_path":"capture.json"}}
            prediction={"event_id":"g","player_id":"p","market":"points",
                        "direction":"over","threshold":10,
                        "issued_at":"2026-10-28T10:00:00Z",
                        "scheduled_start":"2026-10-28T23:00:00Z"}
            args={"cutoff":"2026-10-29T03:00:00Z",
                  "allowed_hosts":{"official.nba.com"}}
            result=reconcile_captured_outcomes([prediction],[final],index,d,**args)
            self.assertEqual(result["results"][0]["result"],"HIT")
            self.assertTrue(result["capture_content_matched"])
            self.assertFalse(result["independently_verified"])
            with self.assertRaises(CertificationHold):
                reconcile_captured_outcomes([prediction],[{**final,"value":11}],index,d,**args)
            Path(d,"capture.json").write_bytes(b"tampered")
            with self.assertRaises(CertificationHold):
                reconcile_captured_outcomes([prediction],[final],index,d,**args)
if __name__=="__main__":
    unittest.main()
