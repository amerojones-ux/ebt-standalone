import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/provider-account-metadata-source-review.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderAccountMetadataSourceReviewWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_manual_protected_first_attempt_only(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn('default: "HOLD"',text)
        self.assertIn('default: "NO"',text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn("inputs.decision != 'HOLD'",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("pull_request:",text)

    def test_permissions_and_actions_are_narrow(self):
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
        needle="ref: " + "$" + "{{ github.sha }}"
        self.assertIn(needle,text)
        self.assertIn("persist-credentials: false",text)

    def test_exact_source_workflows_and_artifacts(self):
        text=self.text
        for fragment in (
            ".github/workflows/sportsdataio-account-metadata-review.yml",
            ".github/workflows/sportradar-account-metadata-review.yml",
            ".github/workflows/rapidapi-account-metadata-review.yml",
            "sportsdataio-account-metadata-claim-$CLAIM_RUN_ID",
            "sportradar-account-metadata-claim-$CLAIM_RUN_ID",
            "rapidapi-account-metadata-claim-$CLAIM_RUN_ID",
        ):
            self.assertIn(fragment,text)
        for fragment in (
            'run.get("event")=="workflow_dispatch"',
            'run.get("run_attempt")==1',
            'run.get("head_branch")=="main"',
            'run.get("status")=="completed"',
            'run.get("conclusion")=="success"',
            'run.get("path")==expected_workflow',
        ):
            self.assertIn(fragment,text)

    def test_zip_ingest_is_strict(self):
        text=self.text
        self.assertIn("claim ZIP file set mismatch",text)
        self.assertIn("nested claim ZIP member forbidden",text)
        self.assertIn("encrypted claim ZIP member forbidden",text)
        self.assertIn("symlink claim ZIP member forbidden",text)
        self.assertIn("claim ZIP member size invalid",text)
        self.assertIn("account_metadata_claim.json",text)
        self.assertIn("account_metadata_claim_attestation.json",text)

    def test_original_claim_is_reverified(self):
        text=self.text
        self.assertIn("verify_account_metadata_claim",text)
        self.assertIn("claim provider mismatch",text)
        self.assertIn("claim run binding mismatch",text)
        self.assertIn("claim source commit mismatch",text)
        self.assertIn("claim source reference mismatch",text)
        self.assertIn("gh attestation verify account_metadata_claim.json",text)
        self.assertIn("--source-digest",text)

    def test_reviewer_identity_and_approval_are_explicit(self):
        text=self.text
        actor_needle="REVIEWER_ACTOR: " + "$" + "{{ github.actor }}"
        actor_id_needle="REVIEWER_ACTOR_ID: " + "$" + "{{ github.actor_id }}"
        self.assertIn(actor_needle,text)
        self.assertIn(actor_id_needle,text)
        self.assertIn("I_APPROVE_ACCOUNT_METADATA_SOURCE_VERIFICATION",text)
        self.assertIn("build_source_review_decision",text)
        self.assertIn("verify_source_review_decision",text)

    def test_review_decision_is_signed_and_verified(self):
        text=self.text
        self.assertIn("subject-path: account_metadata_source_review_decision.json",text)
        self.assertIn("gh attestation verify account_metadata_source_review_decision.json",text)
        self.assertIn(".github/workflows/provider-account-metadata-source-review.yml",text)
        self.assertIn("account_metadata_source_review_attestation.json",text)
        self.assertIn("retention-days: 7",text)

    def test_review_package_is_nonmutating(self):
        text=self.text
        self.assertNotIn("git push",text)
        self.assertNotIn("gh pr",text)
        self.assertNotIn("config/provider_account_evidence.json",text)
        self.assertNotIn("config/provider_readiness.json",text)
        self.assertNotIn('network_request_permitted":True',text)
        self.assertNotIn('forecast_activation_permitted":True',text)

if __name__=="__main__":
    unittest.main()
