import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS={
    "SportsDataIO":ROOT/".github/workflows/sportsdataio-account-metadata-review.yml",
    "Sportradar":ROOT/".github/workflows/sportradar-account-metadata-review.yml",
    "RapidAPI":ROOT/".github/workflows/rapidapi-account-metadata-review.yml",
}
CHECKOUT_SHA="11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA="cf430e030ddbb5b0abf93d22962f4752f3646cd9"
ATTEST_SHA="1e69f48acb82d1966a394da916b4c1698aa569d6"

class ProviderAccountMetadataWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text={k:p.read_text(encoding="utf-8") for k,p in WORKFLOWS.items()}

    def test_manual_protected_first_attempt_only(self):
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn("workflow_dispatch:",text)
                self.assertIn("github.run_attempt == 1",text)
                self.assertIn("github.ref_protected == true",text)
                self.assertIn("github.ref == 'refs/heads/main'",text)
                self.assertNotIn("schedule:",text)
                self.assertNotIn("\npush:",text)
                self.assertNotIn("\n  push:",text)
                self.assertNotIn("pull_request:",text)

    def test_narrow_permissions_and_no_secret_reads(self):
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn("  contents: read",text)
                self.assertIn("  id-token: write",text)
                self.assertIn("  attestations: write",text)
                self.assertIn("  artifact-metadata: write",text)
                self.assertNotIn("contents: write",text)
                self.assertNotIn("actions: write",text)
                self.assertNotIn("secrets.",text)
                self.assertNotIn("EBT_",text)

    def test_actions_pinned_and_checkout_immutable(self):
        needle="ref: " + "$" + "{{ github.sha }}"
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn("actions/checkout@"+CHECKOUT_SHA,text)
                self.assertIn("actions/attest@"+ATTEST_SHA,text)
                self.assertIn("actions/upload-artifact@"+UPLOAD_SHA,text)
                self.assertIn(needle,text)
                self.assertIn("persist-credentials: false",text)
                self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',text)
                self.assertIn('test -z "$(git status --porcelain)"',text)

    def test_claim_is_proposal_only_and_self_verified(self):
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn('"claim_verified_against_provider_source":False',text)
                self.assertIn('"write_permitted":False',text)
                self.assertIn('"network_request_permitted":False',text)
                self.assertIn('"forecast_activation_permitted":False',text)
                self.assertIn("verify_account_metadata_claim",text)
                self.assertIn("generated account metadata claim failed self-verification",text)

    def test_signed_claim_verified_and_short_lived(self):
        expected={
            "SportsDataIO":"sportsdataio-account-metadata-review.yml",
            "Sportradar":"sportradar-account-metadata-review.yml",
            "RapidAPI":"rapidapi-account-metadata-review.yml",
        }
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn("subject-path: account_metadata_claim.json",text)
                self.assertIn("gh attestation verify account_metadata_claim.json",text)
                self.assertIn(expected[provider],text)
                self.assertIn('--source-ref "refs/heads/main"',text)
                self.assertIn('--source-digest "$GITHUB_SHA"',text)
                self.assertIn("account_metadata_claim_attestation.json",text)
                self.assertIn("retention-days: 7",text)
                self.assertIn("if-no-files-found: error",text)

    def test_source_reference_sanitized(self):
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                self.assertIn("[A-Za-z0-9 ._/#()-]{1,160}",text)
                for word in ("token","password","secret","bearer","authorization"):
                    self.assertIn(word,text)

    def test_no_repository_or_provider_mutation_commands(self):
        forbidden=(
            "git push","gh pr","curl ","wget ","requests.","urllib.request",
            "config/provider_readiness.json",
        )
        for provider,text in self.text.items():
            with self.subTest(provider=provider):
                for fragment in forbidden:
                    self.assertNotIn(fragment,text)

    def test_provider_specific_authorization_phrases(self):
        self.assertIn(
            "I_CONFIRM_SPORTSDATAIO_ACCESS_TIER_FEED_AND_QUOTA_REVIEWED",
            self.text["SportsDataIO"],
        )
        self.assertIn(
            "I_APPROVE_SPORTSDATAIO_ACCOUNT_METADATA_CLAIM",
            self.text["SportsDataIO"],
        )
        self.assertIn(
            "I_CONFIRM_SPORTRADAR_NFL_ACCESS_LEVEL_PRODUCT_AND_QUOTA_REVIEWED",
            self.text["Sportradar"],
        )
        self.assertIn(
            "I_APPROVE_SPORTRADAR_ACCOUNT_METADATA_CLAIM",
            self.text["Sportradar"],
        )
        self.assertIn(
            "I_CONFIRM_RAPIDAPI_PRODUCT_HOST_PLAN_QUOTA_AND_OVERAGE_REVIEWED",
            self.text["RapidAPI"],
        )
        self.assertIn(
            "I_APPROVE_RAPIDAPI_ACCOUNT_METADATA_CLAIM",
            self.text["RapidAPI"],
        )

if __name__=="__main__":
    unittest.main()
