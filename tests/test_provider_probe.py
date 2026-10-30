"""Offline-only tests for provider HTTPS probe; never performs network calls."""
import unittest
from extensions.provider_gateway import ProviderGateError
from extensions.provider_probe import ProbeSpec, probe_readonly


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, data=b'{"ok":true}'):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size):
        return self.data[:size]


class FakeOpener:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.request = None
    def open(self, request, timeout):
        self.request = request
        return self.response


SPEC = ProbeSpec("sportradar", "https://api.example.org/health", "api.example.org", "x-api-key")
HOSTS = frozenset({"api.example.org"})


class ProbeTests(unittest.TestCase):
    def test_reachable_is_not_certified(self):
        opener = FakeOpener()
        result = probe_readonly(SPEC, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=opener)
        self.assertEqual(result["connection"], "REACHABLE_ONLY")
        self.assertEqual(result["forecast"], "HOLD")
        self.assertEqual(opener.request.get_method(), "GET")
        self.assertNotIn("SYNTHETIC", str(result))

    def test_unapproved_host_rejected(self):
        with self.assertRaises(ProviderGateError):
            probe_readonly(SPEC, secret="SYNTHETIC", approved_hostnames=frozenset(), opener=FakeOpener())

    def test_query_token_rejected(self):
        spec = ProbeSpec("sportradar", "https://api.example.org/health?key=secret", "api.example.org", "x-api-key")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_host_mismatch_rejected(self):
        spec = ProbeSpec("sportradar", "https://evil.example/health", "api.example.org", "x-api-key")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_ip_literal_rejected(self):
        spec = ProbeSpec("sportradar", "https://127.0.0.1/health", "127.0.0.1", "x-api-key")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=frozenset({"127.0.0.1"}), opener=FakeOpener())

    def test_bad_auth_rejected(self):
        spec = ProbeSpec("sportradar", "https://api.example.org/health", "api.example.org", "query-param")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_secret_newline_rejected(self):
        with self.assertRaises(ProviderGateError):
            probe_readonly(SPEC, secret="secret\r\nX-Evil: 1", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_malformed_json_blocked(self):
        result = probe_readonly(SPEC, secret="SYNTHETIC", approved_hostnames=HOSTS,
                                opener=FakeOpener(FakeResponse(b"not json")))
        self.assertEqual(result["connection"], "BLOCKED")

    def test_oversized_payload_blocked(self):
        result = probe_readonly(SPEC, secret="SYNTHETIC", approved_hostnames=HOSTS,
                                opener=FakeOpener(FakeResponse(b"x" * 65537)))
        self.assertEqual(result["connection"], "BLOCKED")

    def test_invalid_port_rejected(self):
        spec = ProbeSpec("sportradar", "https://api.example.org:bad/health", "api.example.org", "x-api-key")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_nonfinite_timeout_rejected(self):
        spec = ProbeSpec("sportradar", "https://api.example.org/health", "api.example.org", "x-api-key", float("nan"))
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_invalid_provider_type_rejected(self):
        spec = ProbeSpec([], "https://api.example.org/health", "api.example.org", "x-api-key")
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())

    def test_timeout_limit(self):
        spec = ProbeSpec("sportradar", "https://api.example.org/health", "api.example.org", "x-api-key", 30)
        with self.assertRaises(ProviderGateError):
            probe_readonly(spec, secret="SYNTHETIC", approved_hostnames=HOSTS, opener=FakeOpener())


if __name__ == "__main__":
    unittest.main()
