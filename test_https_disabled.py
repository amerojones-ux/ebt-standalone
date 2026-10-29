import tempfile
import unittest
from unittest.mock import patch
from ebt_https_acquire import collect_https
from ebt_certification import CertificationHold

class DisabledCollectorTests(unittest.TestCase):
    def test_default_is_fail_closed_before_dns(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("ebt_https_acquire.socket.getaddrinfo") as lookup:
                with self.assertRaisesRegex(CertificationHold,"experimental"):
                    collect_https("https://official.nba.com/test",d,
                                  allowed_hosts={"official.nba.com"},
                                  collector_version="test")
                lookup.assert_not_called()
if __name__=="__main__":
    unittest.main()
