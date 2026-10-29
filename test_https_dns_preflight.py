import tempfile
import unittest
from unittest.mock import patch
from ebt_https_acquire import collect_https
from ebt_certification import CertificationHold

class DNSPreflightTests(unittest.TestCase):
    def test_private_and_loopback_dns_rejected(self):
        for address in ("127.0.0.1","10.1.2.3","169.254.169.254","::1"):
            with self.subTest(address=address),tempfile.TemporaryDirectory() as d:
                with patch("ebt_https_acquire.socket.getaddrinfo",return_value=[
                    (2,1,6,"",(address,443))]):
                    with self.assertRaises(CertificationHold):
                        collect_https("https://official.nba.com/data",d,
                                      allowed_hosts={"official.nba.com"},
                                      collector_version="test")
    def test_malformed_port_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CertificationHold):
                collect_https("https://official.nba.com:bad/data",d,
                              allowed_hosts={"official.nba.com"},
                              collector_version="test")
if __name__=="__main__":
    unittest.main()
