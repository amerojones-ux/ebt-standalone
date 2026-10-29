import tempfile
import unittest
from ebt_https_acquire import collect_https
from ebt_certification import CertificationHold

class HTTPSAcquisitionTests(unittest.TestCase):
    def test_rejects_unapproved_urls_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            for url in ("http://official.nba.com/test",
                        "https://evil.example/test",
                        "https://official.nba.com:444/test",
                        "https://user:pass@official.nba.com/test",
                        "https://official.nba.com/test#fragment"):
                with self.subTest(url=url),self.assertRaises(CertificationHold):
                    collect_https(url,d,allowed_hosts={"official.nba.com"},
                                  collector_version="test",experimental=True)
    def test_rejects_bad_limits_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CertificationHold):
                collect_https("https://official.nba.com/test",d,
                              allowed_hosts={"official.nba.com"},
                              collector_version="test",max_bytes=0,experimental=True)
if __name__=="__main__":
    unittest.main()
