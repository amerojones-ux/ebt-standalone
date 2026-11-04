import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/provider-account-metadata-promotion-apply.yml"
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderAccountMetadataPromotionApplyWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WORKFLOW.read_text(encoding="utf-8")

    def test_manual_protected_first_attempt_and_exact_authorization(self):
        text=self.text
        self.assertIn("workflow_dispatch:",text)
        self.assertIn("github.run_attempt == 1",text)
        self.assertIn("github.ref_protected == true",text)
        self.assertIn("github.ref == 'refs/heads/main'",text)
        self.assertIn("I_APPROVE_ACCOUNT_METADATA_PROMOTION_APPLY",text)
        self.assertNotIn("schedule:",text)
        self.assertNotIn("\npush:",text)
        self.assertNotIn("pull_request:",text)

    def test_permissions_are_limited_to_branch_apply_requirements(self):
        text=self.text
        self.assertIn("  contents: write",text)
        self.assertIn("  actions: read",text)
        self.assertIn("  id-token: write",text)
        self.assertIn("  attestations: write",text)
        self.assertIn("  artifact-metadata: write",text)
        self.assertNotIn("actions: write",text)
        self.assertNotIn("pull-requests: write",text)
        self.assertNotIn("secrets.",text)
        self.assertNotIn("EBT_",text)

    def test_actions_are_pinned_and_checkout_is_immutable(self):
        text=self.text
        needle="ref: " + "$" + "{{ github.sha }}"
        self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
        self.assertIn("actions/attest@"+ATTEST_SHA,text)
        self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
        self.assertIn(needle,text)
        self.assertIn("persist-credentials: false",text)
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',text)
        self.assertIn('test -z "$(git status --porcelain)"',text)

    def test_phase82_source_run_is_exactly_bound(self):
        text=self.text
        self.assertIn(
            ".github/workflows/provider-account-metadata-promotion-preview.yml",
            text,
        )
        for fragment in (
            "promotion preview run was not workflow_dispatch",
            "promotion preview run was not first attempt",
            "promotion preview run was not main",
            "promotion preview run did not complete successfully",
            "promotion preview workflow path mismatch",
            "promotion preview repository mismatch",
            "promotion preview head repository mismatch",
        ):
            self.assertIn(fragment,text)
        self.assertIn(
            "provider-account-metadata-promotion-preview-([0-9]+)-",
            text,
        )

    def test_preview_zip_is_strictly_whitelisted(self):
        text=self.text
        for filename in (
            "account_metadata_claim.json",
            "account_metadata_source_review_decision.json",
            "account_metadata_source_review_attestation.json",
            "account_metadata_promotion_preview.json",
            "account_metadata_promotion_preview_attestation.json",
        ):
            self.assertIn(filename,text)
        for fragment in (
            "promotion preview ZIP file set mismatch",
            "nested promotion preview ZIP member forbidden",
            "encrypted promotion preview ZIP member forbidden",
            "symlink promotion preview ZIP member forbidden",
            "promotion preview ZIP member size invalid",
        ):
            self.assertIn(fragment,text)

    def test_preview_and_review_are_reverified_before_apply(self):
        text=self.text
        self.assertIn("verify_account_metadata_claim",text)
        self.assertIn("verify_source_review_decision",text)
        self.assertIn("verify_metadata_promotion_preview",text)
        self.assertIn("source review decision invalid/not approved",text)
        self.assertIn("preview claim checksum mismatch",text)
        self.assertIn("preview source-review run mismatch",text)
        self.assertIn("preview review-decision checksum mismatch",text)
        self.assertIn(
            "gh attestation verify account_metadata_promotion_preview.json",
            text,
        )
        self.assertIn("--source-digest",text)

    def test_apply_rebuild_and_exact_file_hashes_are_required(self):
        text=self.text
        self.assertIn("build_metadata_promotion_apply",text)
        self.assertIn("verify_metadata_promotion_apply",text)
        self.assertIn("metadata apply manifest self-verification failed",text)
        self.assertIn("account_evidence_file_sha256",text)
        self.assertIn("provider_config_file_sha256",text)
        self.assertIn("account evidence file checksum mismatch",text)
        self.assertIn("provider config file checksum mismatch",text)

    def test_apply_manifest_is_attested_twice_verified(self):
        text=self.text
        self.assertIn(
            "subject-path: account_metadata_promotion_apply_manifest.json",
            text,
        )
        self.assertEqual(
            text.count(
                "gh attestation verify account_metadata_promotion_apply_manifest.json"
            ),
            2,
        )
        self.assertIn("--bundle",text)
        self.assertIn(
            ".github/workflows/provider-account-metadata-promotion-apply.yml",
            text,
        )

    def test_branch_is_isolated_and_main_must_not_move(self):
        text=self.text
        self.assertIn(
            'current_main="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)"',
            text,
        )
        self.assertIn('test "$current_main" = "$GITHUB_SHA"',text)
        self.assertIn(
            'branch="promotion/$slug-account-metadata-$PREVIEW_RUN_ID-$GITHUB_RUN_ID"',
            text,
        )
        self.assertIn('-f ref="refs/heads/$branch"',text)
        self.assertNotIn('ref="refs/heads/main"',text)

    def test_only_two_expected_content_files_are_written_to_branch(self):
        text=self.text
        self.assertIn(
            'repos/$GITHUB_REPOSITORY/contents/config/provider_account_evidence.json',
            text,
        )
        self.assertIn(
            'repos/$GITHUB_REPOSITORY/contents/$PROVIDER_PATH',
            text,
        )
        self.assertEqual(text.count('-f branch="$branch"'),2)
        self.assertIn(
            "config/provider_account_evidence.json",
            text,
        )
        self.assertNotIn("config/provider_readiness.json",text)
        self.assertNotIn("config/provider_evidence.json",text)

    def test_written_git_blobs_are_verified_against_generated_files(self):
        text=self.text
        self.assertIn(
            "git hash-object generated/provider_account_evidence.json",
            text,
        )
        self.assertIn(
            "git hash-object generated/provider_config.json",
            text,
        )
        self.assertIn(
            'test "$actual_registry_blob" = "$expected_registry_blob"',
            text,
        )
        self.assertIn(
            'test "$actual_provider_blob" = "$expected_provider_blob"',
            text,
        )

    def test_workflow_does_not_open_or_merge_pr_or_call_provider(self):
        text=self.text
        for fragment in (
            "gh pr create","gh pr merge","curl ","wget ","requests.",
            "urllib.request",
        ):
            self.assertNotIn(fragment,text)
        self.assertIn(
            "The workflow intentionally does not open or merge a pull request.",
            text,
        )
        self.assertIn(
            "No provider request, forecast activation, or model-evidence activation occurred.",
            text,
        )

    def test_apply_evidence_is_short_lived_and_sanitized(self):
        text=self.text
        self.assertIn(
            "provider-account-metadata-promotion-apply-",
            text,
        )
        self.assertIn("account_metadata_promotion_apply_manifest.json",text)
        self.assertIn("generated/provider_account_evidence.json",text)
        self.assertIn("generated/provider_config.json",text)
        self.assertIn("retention-days: 7",text)
        self.assertIn("if-no-files-found: error",text)

if __name__=="__main__":
    unittest.main()
