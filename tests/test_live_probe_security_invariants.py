import pathlib
import unittest
from unittest.mock import Mock, patch

import apisports_status_probe
import theoddsapi_live_probe
import weatherapi_live_probe


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = {
    "weather": ROOT / ".github" / "workflows" / "weatherapi-live-probe.yml",
    "odds": ROOT / ".github" / "workflows" / "theoddsapi-live-probe.yml",
    "apisports": ROOT / ".github" / "workflows" / "apisports-status-probe.yml",
}


class LiveProbeSecurityInvariantTests(unittest.TestCase):
    def test_live_workflows_are_manual_main_only_and_read_only(self):
        for name, path in WORKFLOWS.items():
            with self.subTest(name=name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("workflow_dispatch:", text)
                self.assertIn("github.ref == 'refs/heads/main'", text)
                self.assertIn("ref: main", text)
                self.assertIn("persist-credentials: false", text)
                self.assertIn("permissions:\n  contents: read", text)
                self.assertNotIn("schedule:", text)
                self.assertNotIn("pull_request:", text)
                self.assertNotIn("\npush:", text)
                self.assertNotIn("\n  push:", text)
                self.assertIn('default: "NO"', text)
                self.assertIn("verify_receipt", text)

    def _assert_direct_no_proxy_opener(self, module):
        fake_opener = Mock()
        fake_response = object()
        fake_opener.open.return_value = fake_response
        fake_opener.addheaders = [("User-agent", "unsafe")]
        with patch.object(
            module.urllib.request,
            "build_opener",
            return_value=fake_opener,
        ) as build:
            result = module._default_open(object(), 10)
        self.assertIs(result, fake_response)
        handlers = build.call_args.args
        proxy_handlers = [
            handler for handler in handlers
            if isinstance(handler, module.urllib.request.ProxyHandler)
        ]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})
        self.assertTrue(
            any(isinstance(handler, module.NoRedirectHandler) for handler in handlers)
        )
        fake_opener.open.assert_called_once()
        return fake_opener

    def test_weatherapi_default_opener_disables_environment_proxies(self):
        self._assert_direct_no_proxy_opener(weatherapi_live_probe)

    def test_theoddsapi_default_opener_disables_environment_proxies(self):
        self._assert_direct_no_proxy_opener(theoddsapi_live_probe)

    def test_apisports_default_opener_disables_proxies_and_default_headers(self):
        opener = self._assert_direct_no_proxy_opener(apisports_status_probe)
        self.assertEqual(opener.addheaders, [])


if __name__ == "__main__":
    unittest.main()
