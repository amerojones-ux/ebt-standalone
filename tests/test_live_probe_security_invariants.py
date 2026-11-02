import pathlib
import unittest
from unittest.mock import Mock, patch

import apisports_status_probe
import theoddsapi_live_probe
import weatherapi_live_probe


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = {
    "weather": {
        "path": ROOT / ".github" / "workflows" / "weatherapi-live-probe.yml",
        "receipt": "weatherapi_probe_receipt.json",
        "artifact_prefix": "weatherapi-probe-receipt",
        "marker": "weatherapi_attestation_verification.json",
        "marker_prefix": "weatherapi-attestation-verification",
        "signer": ".github/workflows/weatherapi-live-probe.yml",
    },
    "odds": {
        "path": ROOT / ".github" / "workflows" / "theoddsapi-live-probe.yml",
        "receipt": "theoddsapi_probe_receipt.json",
        "artifact_prefix": "theoddsapi-probe-receipt",
        "marker": "theoddsapi_attestation_verification.json",
        "marker_prefix": "theoddsapi-attestation-verification",
        "signer": ".github/workflows/theoddsapi-live-probe.yml",
    },
    "apisports": {
        "path": ROOT / ".github" / "workflows" / "apisports-status-probe.yml",
        "receipt": "apisports_status_receipt.json",
        "artifact_prefix": "apisports-status-receipt",
        "marker": "apisports_attestation_verification.json",
        "marker_prefix": "apisports-attestation-verification",
        "signer": ".github/workflows/apisports-status-probe.yml",
    },
}
UPLOAD_ARTIFACT_SHA = "cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA = "1e69f48acb82d1966a394da916b4c1698aa569d6"


class LiveProbeSecurityInvariantTests(unittest.TestCase):
    def test_live_workflows_are_manual_main_only_and_read_only(self):
        for name, spec in WORKFLOWS.items():
            with self.subTest(name=name):
                text = spec["path"].read_text(encoding="utf-8")
                self.assertIn("workflow_dispatch:", text)
                self.assertIn("github.ref == 'refs/heads/main'", text)
                self.assertIn("ref: main", text)
                self.assertIn("persist-credentials: false", text)
                self.assertIn("permissions:\n  contents: read", text)
                self.assertIn("  id-token: write", text)
                self.assertIn("  attestations: write", text)
                self.assertIn("  artifact-metadata: write", text)
                self.assertNotIn("schedule:", text)
                self.assertNotIn("pull_request:", text)
                self.assertNotIn("\npush:", text)
                self.assertNotIn("\n  push:", text)
                self.assertIn('default: "NO"', text)
                self.assertIn("verify_receipt", text)

    def test_live_workflows_persist_only_sanitized_evidence_artifacts(self):
        for name, spec in WORKFLOWS.items():
            with self.subTest(name=name):
                text = spec["path"].read_text(encoding="utf-8")
                self.assertIn(
                    "actions/upload-artifact@" + UPLOAD_ARTIFACT_SHA,
                    text,
                )
                self.assertIn(
                    "name: " + spec["artifact_prefix"] + "-${{ github.run_id }}",
                    text,
                )
                self.assertIn("path: " + spec["receipt"], text)
                self.assertIn("if-no-files-found: ignore", text)
                self.assertIn(
                    "name: " + spec["marker_prefix"] + "-${{ github.run_id }}",
                    text,
                )
                self.assertIn("path: " + spec["marker"], text)
                self.assertIn("if-no-files-found: error", text)
                self.assertIn("retention-days: 7", text)
                self.assertIn("compression-level: 0", text)
                self.assertNotIn("path: .", text)
                self.assertNotIn("path: ./", text)
                self.assertNotIn("path: **", text)
                self.assertNotIn("raw_response", text)

    def test_live_workflows_attest_and_verify_exact_receipt_identity(self):
        for name, spec in WORKFLOWS.items():
            with self.subTest(name=name):
                text = spec["path"].read_text(encoding="utf-8")
                self.assertIn("id: probe", text)
                self.assertIn(
                    'echo "receipt_verified=$receipt_ok" >> "$GITHUB_OUTPUT"',
                    text,
                )
                self.assertIn("id: attest", text)
                self.assertIn(
                    "if: always() && steps.probe.outputs.receipt_verified == '1'",
                    text,
                )
                self.assertIn("actions/attest@" + ATTEST_SHA, text)
                self.assertIn("subject-path: " + spec["receipt"], text)
                self.assertIn("id: verify_attestation", text)
                self.assertIn('gh attestation verify "$RECEIPT_FILE"', text)
                self.assertIn('--repo "$GITHUB_REPOSITORY"', text)
                self.assertIn(
                    '--signer-workflow "$GITHUB_REPOSITORY/$SIGNER_WORKFLOW"',
                    text,
                )
                self.assertIn('--source-ref "refs/heads/main"', text)
                self.assertIn('--source-digest "$GITHUB_SHA"', text)
                self.assertIn("SIGNER_WORKFLOW: " + spec["signer"], text)
                self.assertIn(
                    'echo "attestation_verified=1" >> "$GITHUB_OUTPUT"',
                    text,
                )

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
