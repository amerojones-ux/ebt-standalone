import hashlib
import tempfile
import unittest
from pathlib import Path
from ebt_capture_index import verify_capture, corroborate_distinct_sources
from ebt_certification import CertificationHold

class CaptureIndexTests(unittest.TestCase):
    def test_integrity_and_host_separation(self):
        with tempfile.TemporaryDirectory() as d:
            index = {}
            for i,host in enumerate(("official.nba.com","www.teamrankings.com")):
                body = ("synthetic-" + str(i)).encode()
                filename = "capture-" + str(i) + ".bin"
                Path(d,filename).write_bytes(body)
                index[str(i)] = {"sha256":hashlib.sha256(body).hexdigest(),
                    "url":"https://"+host+"/synthetic","retrieved_at":"2026-10-28T12:00:00Z",
                    "raw_path":filename}
            args = dict(cutoff="2026-10-28T13:00:00Z",
                        allowed_hosts={"official.nba.com","www.teamrankings.com"})
            result = corroborate_distinct_sources(["0","1"],index,d,**args)
            self.assertTrue(result["integrity_verified"])
            self.assertFalse(result["independent_truth_certified"])
            with self.assertRaises(CertificationHold):
                corroborate_distinct_sources(["0","0"],index,d,**args)
            with self.assertRaises(CertificationHold):
                verify_capture("0",index,d,cutoff="2026-10-28T11:00:00Z",allowed_hosts=args["allowed_hosts"])
            index["1"]["url"] = "https://official.nba.com/another"
            with self.assertRaises(CertificationHold):
                corroborate_distinct_sources(["0","1"],index,d,**args)
            Path(d,"capture-0.bin").write_bytes(b"tampered")
            with self.assertRaises(CertificationHold):
                verify_capture("0",index,d,**args)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            index = {"x":{"sha256":"0"*64,"url":"https://official.nba.com/a",
                          "retrieved_at":"2026-10-28T12:00:00Z","raw_path":"../outside"}}
            with self.assertRaises(CertificationHold):
                verify_capture("x",index,d,cutoff="2026-10-28T13:00:00Z",allowed_hosts={"official.nba.com"})

if __name__ == "__main__":
    unittest.main()
