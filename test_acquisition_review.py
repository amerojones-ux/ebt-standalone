import hashlib
import tempfile
import unittest
from pathlib import Path
from ebt_acquisition_review import acquisition_review
from ebt_certification import CertificationHold

class AcquisitionReviewTests(unittest.TestCase):
    def test_metadata_review_never_authenticates_source(self):
        with tempfile.TemporaryDirectory() as d:
            body=b"synthetic"
            Path(d,"raw").write_bytes(body)
            att={"method":"authorized_api","collector_version":"test",
                 "request_id":"fixture","tls_verified":True,"http_status":200,
                 "completed_at":"2026-10-28T11:59:00Z"}
            entry={"sha256":hashlib.sha256(body).hexdigest(),
                   "url":"https://official.nba.com/test","raw_path":"raw",
                   "retrieved_at":"2026-10-28T12:00:00Z","acquisition":att}
            index={"x":entry}
            args={"cutoff":"2026-10-28T13:00:00Z",
                  "allowed_hosts":{"official.nba.com"}}
            result=acquisition_review("x",index,d,**args)
            self.assertFalse(result["provider_authenticity_verified"])
            self.assertTrue(result["manual_acquisition_review_required"])
            for bad in ({"tls_verified":False},{"http_status":403},
                        {"completed_at":"2026-10-28T12:01:00Z"}):
                with self.subTest(bad=bad),self.assertRaises(CertificationHold):
                    acquisition_review("x",{"x":{**entry,"acquisition":{**att,**bad}}},d,**args)
if __name__=="__main__":
    unittest.main()
