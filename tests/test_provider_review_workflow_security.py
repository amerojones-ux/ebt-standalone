import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github"/"workflows"/"provider-live-auth-evidence-review.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderReviewWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_manual_default_hold_only(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn('default: "HOLD"',text)
        self.assertIn('default: "NO"',text)
        self.assertIn("inputs.decision != 'HOLD'",text)
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
        self.assertNotIn("secrets.",text)
        self.assertNotIn("EBT_",text)
        self.assertNotIn("contents: write",text)
        self.assertNotIn("actions: write",text)

    def test_checkout_and_actions_are_immutable(self):
        text=self.text
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("persist-credentials: false",text)

    def test_source_run_must_be_exact_completed_probe(self):
        text=self.text
        for workflow in (
            ".github/workflows/weatherapi-live-probe.yml",
            ".github/workflows/theoddsapi-live-probe.yml",
            ".github/workflows/apisports-status-probe.yml",
        ):
            self.assertIn(workflow,text)
        self.assertIn('run.get("event") != "workflow_dispatch"',text)
        self.assertIn('run.get("head_branch") != "main"',text)
        self.assertIn('run.get("status") != "completed"',text)
        self.assertIn('run.get("conclusion") != "success"',text)
        self.assertIn('run.get("path") != expected_workflow',text)
        self.assertIn('repository.get("full_name") != os.environ["GITHUB_REPOSITORY"]',text)

    def test_exact_receipt_bundle_and_execution_intent_artifacts_are_required(self):
        text=self.text
        for fragment in (
            "weatherapi-probe-receipt-$SOURCE_RUN_ID",
            "weatherapi-attestation-verification-$SOURCE_RUN_ID",
            "weatherapi-attestation-bundle-$SOURCE_RUN_ID",
            "weatherapi-execution-intent-$SOURCE_RUN_ID",
            "weatherapi-execution-intent-attestation-verification-$SOURCE_RUN_ID",
            "weatherapi-execution-intent-attestation-bundle-$SOURCE_RUN_ID",
            "theoddsapi-probe-receipt-$SOURCE_RUN_ID",
            "theoddsapi-attestation-verification-$SOURCE_RUN_ID",
            "theoddsapi-attestation-bundle-$SOURCE_RUN_ID",
            "theoddsapi-execution-intent-$SOURCE_RUN_ID",
            "theoddsapi-execution-intent-attestation-verification-$SOURCE_RUN_ID",
            "theoddsapi-execution-intent-attestation-bundle-$SOURCE_RUN_ID",
            "apisports-status-receipt-$SOURCE_RUN_ID",
            "apisports-attestation-verification-$SOURCE_RUN_ID",
            "apisports-attestation-bundle-$SOURCE_RUN_ID",
            "apisports-execution-intent-$SOURCE_RUN_ID",
            "apisports-execution-intent-attestation-verification-$SOURCE_RUN_ID",
            "apisports-execution-intent-attestation-bundle-$SOURCE_RUN_ID",
        ):
            self.assertIn(fragment,text)
        self.assertIn("artifact count mismatch",text)
        self.assertIn("artifact expired",text)
        self.assertIn("provider_github_artifact_ingest_cli.py",text)
        for fragment in (
            "receipt_metadata.json receipt.zip",
            "marker_metadata.json marker.zip",
            "bundle_metadata.json bundle.zip",
            "intent_metadata.json intent.zip",
            "intent_marker_metadata.json intent_marker.zip",
            "intent_bundle_metadata.json intent_bundle.zip",
        ):
            self.assertIn(fragment,text)

    def test_reviewer_identity_comes_from_github_actor(self):
        text=self.text
        self.assertIn("REVIEWER_ACTOR: ${{ github.actor }}",text)
        self.assertIn("REVIEWER_ACTOR_ID: ${{ github.actor_id }}",text)
        self.assertIn('reviewer="github:$REVIEWER_ACTOR#$REVIEWER_ACTOR_ID"',text)
        self.assertNotIn("reviewer:",text.split("inputs:",1)[1].split("permissions:",1)[0])

    def test_review_decision_is_attested_and_verified(self):
        text=self.text
        self.assertIn("--output provider_review_decision.json",text)
        self.assertIn("subject-path: provider_review_decision.json",text)
        self.assertIn("id: verify_review_attestation",text)
        self.assertIn("gh attestation verify provider_review_decision.json",text)
        self.assertIn(
            '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/provider-live-auth-evidence-review.yml"',
            text,
        )
        self.assertIn('--source-ref "refs/heads/main"',text)
        self.assertIn('--source-digest "$GITHUB_SHA"',text)
        self.assertIn("provider_review_decision_attestation_verification.json",text)

    def test_review_package_is_sanitized_and_nonmutating(self):
        text=self.text
        self.assertIn("provider_review_candidate.json",text)
        self.assertIn("provider_review_decision.json",text)
        self.assertIn("provider_review_decision_attestation_verification.json",text)
        self.assertIn("retention-days: 7",text)
        self.assertIn("if-no-files-found: error",text)
        self.assertNotIn("config/provider_evidence.json",text)
        self.assertNotIn("config/provider_readiness.json",text)
        self.assertNotIn("git push",text)
        self.assertNotIn("gh pr",text)

if __name__=="__main__":
    unittest.main()
