import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github"/"workflows"/"provider-live-auth-promotion-apply.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"

class PromotionApplyWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_exact_manual_authorization_and_protected_main(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("I_APPROVE_LIVE_AUTH_PROMOTION_APPLY",text)
        self.assertIn('default: "NO"',text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn(
            "concurrency:\n  group: ebt-live-auth-promotion-apply\n"
            "  cancel-in-progress: false",
            text,
        )
        self.assertNotIn("schedule:",text)
        self.assertNotIn("pull_request:\n",text)
        self.assertNotIn("\npush:",text)

    def test_write_permissions_are_limited_to_branch_preparation(self):
        text=self.text
        self.assertIn("  contents: write",text)
        self.assertNotIn("pull-requests: write",text)
        self.assertIn("  actions: read",text)
        self.assertNotIn("actions: write",text)
        self.assertNotIn("secrets.",text)
        self.assertNotIn("EBT_",text)

    def test_immutable_checkout_and_signed_preview_source(self):
        text=self.text
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("ref: ${{ github.sha }}",text)
        self.assertIn("persist-credentials: false",text)
        self.assertIn("Verify immutable apply source checkout",text)
        self.assertIn(
            ".github/workflows/provider-live-auth-promotion-preview.yml",
            text,
        )
        self.assertIn('run.get("run_attempt")!=1',text)
        self.assertIn('run.get("head_branch")!="main"',text)
        self.assertIn('run.get("conclusion")!="success"',text)
        self.assertIn("provider_promotion_preview_package_ingest_cli.py",text)

    def test_apply_remains_safe_hold_and_no_provider_network(self):
        text=self.text
        self.assertIn("provider_live_auth_promotion_apply_cli.py",text)
        self.assertIn('manifest.get("global_provider_gate")!="SAFE_HOLD"',text)
        self.assertIn('manifest.get("forecast_enabled") is not False',text)
        self.assertIn('manifest.get("network_autorun_enabled") is not False',text)
        self.assertIn('manifest.get("provider_network_request_permitted") is not False',text)
        for forbidden in (
            "weatherapi_live_probe.py",
            "theoddsapi_live_probe.py",
            "apisports_status_probe.py",
            "api.weatherapi.com",
            "api.the-odds-api.com",
        ):
            self.assertNotIn(forbidden,text)

    def test_manifest_is_attested_before_branch_creation(self):
        text=self.text
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("subject-path: provider_live_auth_promotion_apply_manifest.json",text)
        self.assertGreaterEqual(
            text.count(
                "gh attestation verify "
                "provider_live_auth_promotion_apply_manifest.json"
            ),
            2,
        )
        verify_index=text.index('echo "apply_attestation_verified=1"')
        branch_index=text.index("- name: Create protected promotion branch")
        self.assertLess(verify_index,branch_index)

    def test_workflow_prepares_branch_but_never_opens_or_merges_pr(self):
        text=self.text
        self.assertIn('git/ref/heads/main',text)
        self.assertIn('test "$current_main" = "$GITHUB_SHA"',text)
        self.assertIn('refs/heads/$branch',text)
        self.assertIn('contents/config/provider_evidence.json',text)
        self.assertIn('contents/config/provider_readiness.json',text)
        self.assertIn('promotion_branch=%s',text)
        self.assertIn("The workflow intentionally does not open or merge a pull request.",text)
        self.assertNotIn('repos/$GITHUB_REPOSITORY/pulls',text)
        self.assertNotIn("merge_pull_request",text)
        self.assertNotIn("/merges",text)
        self.assertNotIn("git push",text)
        self.assertNotIn("forecast_enabled: true",text)
        self.assertNotIn("network_autorun_enabled: true",text)

    def test_apply_evidence_is_short_lived_and_sanitized(self):
        text=self.text
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
        self.assertIn("provider_live_auth_promotion_apply_manifest.json",text)
        self.assertIn("generated/provider_readiness.json",text)
        self.assertIn("generated/provider_evidence.json",text)
        self.assertIn("retention-days: 7",text)
        self.assertIn("compression-level: 0",text)

if __name__=="__main__":
    unittest.main()
