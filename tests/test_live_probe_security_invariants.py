import pathlib
import unittest
from unittest.mock import Mock, patch

import theoddsapi_live_probe
import weatherapi_live_probe


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = {
    "weather": ROOT / ".github" / "workflows" / "weatherapi-live-probe.yml",
    "odds": ROOT / ".github" / "workflows" / "theoddsapi-live-probe.yml",
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

    def test_weatherapi_default_opener_disables_environment_proxies(self):
        fake_opener = Mock()
        fake_response = object()
        fake_opener.open.return_value = fake_response
        with patch.object(
            weatherapi_live_probe.urllib.request,
            "build_opener",
            return_value=fake_opener,
        ) as build:
            result = weatherapi_live_probe._default_open(object(), 10)
        self.assertIs(result, fake_response)
        handlers = build.call_args.args
        proxy_handlers = [
            handler for handler in handlers
            if isinstance(handler, weatherapi_live_probe.urllib.request.ProxyHandler)
        ]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})
        self.assertTrue(
            any(isinstance(handler, weatherapi_live_probe.NoRedirectHandler) for handler in handlers)
        )
        fake_opener.open.assert_called_once()

    def test_theoddsapi_default_opener_disables_environment_proxies(self):
        fake_opener = Mock()
        fake_response = object()
        fake_opener.open.return_value = fake_response
        with patch.object(
            theoddsapi_live_probe.urllib.request,
            "build_opener",
            return_value=fake_opener,
        ) as build:
            result = theoddsapi_live_probe._default_open(object(), 10)
        self.assertIs(result, fake_response)
        handlers = build.call_args.args
        proxy_handlers = [
            handler for handler in handlers
            if isinstance(handler, theoddsapi_live_probe.urllib.request.ProxyHandler)
        ]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})
        self.assertTrue(
            any(isinstance(handler, theoddsapi_live_probe.NoRedirectHandler) for handler in handlers)
        )
        fake_opener.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
