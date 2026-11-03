import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github"/"workflows"/"provider-live-auth-promotion-preview.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderPromotionPreviewWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_manual_default_no_main_only(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn('default: "NO"',text)
        self.assertIn("I_APPROVE_LIVE_AUTH_PROMOTION_PREVIEW",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("pull_request:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("\n  push:",text)

    def test_permissions_are_narrow_and_no_provider_secrets_exist(self):
        text=self.text
        self.assertIn("  contents: read",text)
        self.assertIn("  actions: read",text)
        self.assertIn("  id-token: write",text)
        self.assertIn("  attestations: write",text)
        self.assertIn("  artifact-metadata: write",text)
        self.assertNotIn("contents: write",text)
        self.assertNotIn("actions: write",text)
        self.assertNotIn("secrets.",text)
        self.assertNotIn("EBT_",text)

    def test_immutable_actions_and_checkout(self):
        text=self.text
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
        self.assertIn("persist-credentials: false",text)

    def test_source_review_run_is_exact_completed_main_workflow(self):
        text=self.text
        self.assertIn(
            'expected_workflow = ".github/workflows/provider-live-auth-evidence-review.yml"',
            text,
        )
        self.assertIn('run.get("event") != "workflow_dispatch"',text)
        self.assertIn('run.get("run_attempt") != 1',text)
        self.assertIn('run.get("head_branch") != "main"',text)
        self.assertIn('run.get("status") != "completed"',text)
        self.assertIn('run.get("conclusion") != "success"',text)
        self.assertIn('run.get("path") != expected_workflow',text)
        self.assertIn('repository.get("full_name") != os.environ["GITHUB_REPOSITORY"]',text)

    def test_exact_review_package_is_required(self):
        text=self.text
        self.assertIn(
            'r"^provider-live-auth-review-([0-9]+)-"',
            text,
        )
        self.assertIn("signed review package artifact count mismatch",text)
        self.assertIn("signed review package artifact expired",text)
        self.assertIn('"run_attempt": run["run_attempt"]',text)
        self.assertIn("provider_review_package_ingest_cli.py",text)
        self.assertIn('--repository "$GITHUB_REPOSITORY"',text)
        self.assertIn("--output provider_attested_review_decision.json",text)

    def test_preview_uses_committed_ledger_and_readiness_without_writes(self):
        text=self.text
        self.assertIn("provider_live_auth_promotion_preview_cli.py",text)
        self.assertIn("config/provider_readiness.json",text)
        self.assertIn("config/provider_evidence.json",text)
        self.assertIn("provider_attested_review_decision.json",text)
        self.assertIn('preview.get("global_provider_gate") != "SAFE_HOLD"',text)
        self.assertIn('preview.get("ledger_write_permitted") is not False',text)
        self.assertIn('preview.get("readiness_write_permitted") is not False',text)
        self.assertIn('preview.get("forecast_activation_permitted") is not False',text)
        self.assertNotIn("git push",text)
        self.assertNotIn("gh pr",text)

    def test_preview_is_attested_and_verified(self):
        text=self.text
        self.assertIn("subject-path: provider_live_auth_promotion_preview.json",text)
        self.assertIn(
            "gh attestation verify provider_live_auth_promotion_preview.json",
            text,
        )
        self.assertIn(
            '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/provider-live-auth-promotion-preview.yml"',
            text,
        )
        self.assertIn('--source-ref "refs/heads/main"',text)
        self.assertIn('--source-digest "$GITHUB_SHA"',text)
        self.assertIn("provider_live_auth_promotion_preview_attestation_verification.json",text)

    def test_uploaded_package_is_sanitized_and_short_lived(self):
        text=self.text
        self.assertIn("provider_attested_review_decision.json",text)
        self.assertIn("provider_live_auth_promotion_preview.json",text)
        self.assertIn(
            "provider_live_auth_promotion_preview_attestation_verification.json",
            text,
        )
        self.assertIn("if-no-files-found: error",text)
        self.assertIn("retention-days: 7",text)
        self.assertIn("compression-level: 0",text)

    def test_no_provider_network_probe_is_invoked(self):
        text=self.text
        for forbidden in (
            "weatherapi_live_probe.py",
            "theoddsapi_live_probe.py",
            "apisports_status_probe.py",
        ):
            self.assertNotIn(forbidden,text)

if __name__=="__main__":
    unittest.main()
