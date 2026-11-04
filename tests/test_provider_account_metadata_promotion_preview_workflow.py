import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/provider-account-metadata-promotion-preview.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderAccountMetadataPromotionPreviewWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_manual_protected_first_attempt_only(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn("I_APPROVE_ACCOUNT_METADATA_PROMOTION_PREVIEW",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("pull_request:",text)

    def test_permissions_and_pinned_actions(self):
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
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)

    def test_phase81_run_and_artifact_are_exactly_bound(self):
        text=self.text
        self.assertIn(".github/workflows/provider-account-metadata-source-review.yml",text)
        self.assertIn("source review was not workflow_dispatch",text)
        self.assertIn("source review was not first attempt",text)
        self.assertIn("source review was not main",text)
        self.assertIn("source review did not complete successfully",text)
        self.assertIn("source review workflow path mismatch",text)
        self.assertIn(
            "provider-account-metadata-source-review-([0-9]+)-",
            text,
        )
        self.assertIn("source-review artifact count mismatch",text)

    def test_source_review_zip_is_strict(self):
        text=self.text
        for fragment in (
            "source-review ZIP file set mismatch",
            "nested source-review ZIP member forbidden",
            "encrypted source-review ZIP member forbidden",
            "symlink source-review ZIP member forbidden",
            "source-review ZIP member size invalid",
        ):
            self.assertIn(fragment,text)
        for filename in (
            "account_metadata_claim.json",
            "account_metadata_claim_attestation.json",
            "account_metadata_source_review_decision.json",
            "account_metadata_source_review_attestation.json",
        ):
            self.assertIn(filename,text)

    def test_approved_source_review_is_reverified(self):
        text=self.text
        self.assertIn("verify_account_metadata_claim",text)
        self.assertIn("verify_source_review_decision",text)
        self.assertIn("source review decision not approved",text)
        self.assertIn("decision claim checksum mismatch",text)
        self.assertIn("decision transition mismatch",text)
        self.assertIn("source review marker signer mismatch",text)
        self.assertIn(
            "gh attestation verify account_metadata_source_review_decision.json",
            text,
        )

    def test_current_state_is_rebuilt_and_preview_self_verified(self):
        text=self.text
        self.assertIn("build_metadata_promotion_preview",text)
        self.assertIn("verify_metadata_promotion_preview",text)
        self.assertIn("promotion preview self-verification failed",text)
        self.assertIn("SOURCE_REVIEW_RUN_ID",text)
        self.assertIn("SOURCE_REVIEW_COMMIT",text)

    def test_preview_is_attested_and_short_lived(self):
        text=self.text
        self.assertIn("subject-path: account_metadata_promotion_preview.json",text)
        self.assertIn("gh attestation verify account_metadata_promotion_preview.json",text)
        self.assertIn(".github/workflows/provider-account-metadata-promotion-preview.yml",text)
        self.assertIn("account_metadata_promotion_preview_attestation.json",text)
        self.assertIn("retention-days: 7",text)

    def test_preview_workflow_never_mutates_repository_or_provider(self):
        text=self.text
        for fragment in (
            "git push","gh pr","curl ","wget ","requests.","urllib.request",
            "contents: write","config/provider_readiness.json",
        ):
            self.assertNotIn(fragment,text)

if __name__=="__main__":
    unittest.main()
