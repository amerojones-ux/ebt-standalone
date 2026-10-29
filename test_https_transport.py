"""Transport-level regression tests; no external network calls."""
import ssl
import tempfile
import unittest
from unittest.mock import patch
from ebt_https_acquire import collect_https
from ebt_certification import CertificationHold

class TransportTests(unittest.TestCase):
    def test_dns_changes_block_before_socket(self):
        # Preflight approves a public IP; second lookup returns a private IP.
        first=[(2,1,6,"",("8.8.8.8",443))]
        second=[(2,1,6,"",("127.0.0.1",443))]
        with tempfile.TemporaryDirectory() as d:
            with patch("ebt_https_acquire.socket.getaddrinfo",side_effect=[first,second]), \
                 patch("socket.create_connection") as connect:
                with self.assertRaises((CertificationHold,OSError)):
                    collect_https("https://official.nba.com/test",d,
                                  allowed_hosts={"official.nba.com"},
                                  collector_version="test")
                connect.assert_not_called()
    def test_invalid_url_does_not_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("ebt_https_acquire.socket.getaddrinfo") as lookup:
                with self.assertRaises(CertificationHold):
                    collect_https("https://127.0.0.1/test",d,
                                  allowed_hosts={"official.nba.com"},
                                  collector_version="test")
                lookup.assert_not_called()
if __name__=="__main__":
    unittest.main()
